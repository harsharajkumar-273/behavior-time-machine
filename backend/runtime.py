import hashlib
import importlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from threading import BoundedSemaphore

from .contracts import ROOT, Case, ManifestError, get_case
from .fees import PortVersion

RUN_SLOTS = BoundedSemaphore(4)


class InterpreterError(Exception):
    pass


def run_case(case: Case, lower: int, upper: int, version: PortVersion) -> dict:
    if not case.minimum <= lower <= upper <= case.maximum:
        raise ValueError("Input is outside the declared domain.")
    basic_bytes = (ROOT / case.basicFile).read_bytes()
    port_bytes = (ROOT / case.portFile).read_bytes()
    source = basic_bytes.decode("ascii")
    from .basic_worker import build_driver
    try:
        driver = build_driver(source, lower, upper)
        module = importlib.import_module("backend." + case.portFile.removesuffix(".py"))
        calculate = getattr(module, case.portFunction)
    except (ValueError, ImportError, AttributeError) as error:
        raise ManifestError("The case does not satisfy the scalar program contract.") from error

    if not RUN_SLOTS.acquire(blocking=False):
        raise InterpreterError("The BASIC runtime is busy. Try again in a moment.")
    try:
        process = subprocess.run(
            [sys.executable, str(ROOT / "basic_worker.py")],
            input=json.dumps({"source": source, "minimum": lower, "maximum": upper}),
            capture_output=True, text=True, encoding="utf-8", timeout=15, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise InterpreterError("PC-BASIC timed out. Try again.") from error
    except (OSError, UnicodeError) as error:
        raise InterpreterError("PC-BASIC could not be started or read.") from error
    finally:
        RUN_SLOTS.release()
    if process.returncode:
        raise InterpreterError("PC-BASIC is unavailable or exited with an error.")
    lines = process.stdout.splitlines()
    if len(lines) != upper - lower + 1 or any(re.fullmatch(r" *-?[0-9]+ *", line) is None for line in lines):
        raise InterpreterError("PC-BASIC must return exactly one integer per input line.")
    policy = source.splitlines()[1:-1]
    comparisons = []
    for value, line in zip(range(lower, upper + 1), lines, strict=True):
        legacy = int(line)
        modern = calculate(value, version)
        if type(modern) is not int:
            raise InterpreterError("The port must return an integer.")
        comparisons.append({
            "input": value, "daysOverdue": value,
            "legacyCents": legacy, "modernCents": modern, "matches": legacy == modern,
            "legacyOutput": line.strip(), "policyLines": policy,
        })
    mismatches = [row for row in comparisons if not row["matches"]]
    return {
        "schemaVersion": 2, "caseId": case.id, "portVersion": version,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "manifest": case.model_dump(), "range": {"minimum": lower, "maximum": upper},
        "sourceHashes": {
            "basic": hashlib.sha256(basic_bytes).hexdigest(),
            "port": hashlib.sha256(port_bytes).hexdigest(),
            "driver": hashlib.sha256(driver.encode("ascii")).hexdigest(),
        },
        "runtime": "PC-BASIC 2.0.7",
        "checkedCount": len(comparisons), "mismatchCount": len(mismatches),
        "firstMismatch": mismatches[0] if mismatches else None,
        "mismatches": mismatches, "comparisons": comparisons,
    }


def run_basic(days: list[int]) -> list[int]:
    """Compatibility entry point for the original library boundary checks."""
    case = get_case("library")
    if not days or any(type(day) is not int or not 0 <= day <= 365 for day in days):
        raise ValueError("Days overdue must be whole numbers from 0 to 365.")
    report = run_case(case, min(days), max(days), "corrected")
    fees = {row["input"]: row["legacyCents"] for row in report["comparisons"]}
    return [fees[day] for day in days]
