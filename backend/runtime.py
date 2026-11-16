import re
import subprocess
import sys
from pathlib import Path
from threading import BoundedSemaphore

from .fees import MAX_DAYS

FIXTURE = Path(__file__).with_name("overdue.bas")
POLICY_LINES = tuple(line for line in FIXTURE.read_text().splitlines() if line[:2] in {"40", "50", "60"})
RUN_SLOTS = BoundedSemaphore(4)
PROMPT = re.compile(r"\?\s+([0-9]+)")
FEE_LINE = re.compile(r"(?:\?\s*)*FEE=\s*([0-9]+)\s*")


class InterpreterError(Exception):
    pass


def run_basic(days: list[int]) -> list[int]:
    if not days or len(days) > MAX_DAYS + 1:
        raise ValueError("Invalid BASIC batch size.")
    if any(type(day) is not int or not 0 <= day <= MAX_DAYS for day in days):
        raise ValueError("Days overdue must be whole numbers from 0 to 365.")

    payload = "\n".join(map(str, [len(days), *days])) + "\n"
    if not RUN_SLOTS.acquire(blocking=False):
        raise InterpreterError("The BASIC runtime is busy. Try again in a moment.")
    try:
        process = subprocess.run(
            [sys.executable, str(FIXTURE.with_name("basic_worker.py"))],
            cwd=FIXTURE.parent,
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=8,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise InterpreterError("PC-BASIC timed out. Try again.") from error
    except (OSError, UnicodeError) as error:
        raise InterpreterError("PC-BASIC could not be started or read.") from error
    finally:
        RUN_SLOTS.release()

    if process.returncode:
        raise InterpreterError("PC-BASIC is unavailable or exited with an error.")
    lines = [line.strip() for line in process.stdout.splitlines() if line.strip()]
    prompts = [int(match[1]) for line in lines if (match := PROMPT.fullmatch(line))]
    if prompts != [len(days), *days]:
        raise InterpreterError("PC-BASIC returned unexpected input prompts.")
    matches = [FEE_LINE.fullmatch(line) for line in lines if not PROMPT.fullmatch(line)]
    if len(matches) != len(days) or any(match is None for match in matches):
        raise InterpreterError("PC-BASIC returned unexpected output.")
    fees = [int(match[1]) for match in matches if match]
    if any(not 0 <= fee <= 1000 for fee in fees):
        raise InterpreterError("PC-BASIC returned an out-of-range fee.")
    return fees
