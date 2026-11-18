"""Reproduce a downloaded report using the locally registered case."""
import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .contracts import ManifestError, get_case
from .runtime import InterpreterError, run_case


class ReplayRange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    minimum: int
    maximum: int


class ReplayRequest(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)
    schemaVersion: Literal[2]
    caseId: str
    portVersion: Literal["flawed", "corrected"]
    range: ReplayRange
    manifest: dict
    sourceHashes: dict[str, str]
    runtime: str
    checkedCount: int = Field(ge=1, le=10000)
    mismatchCount: int = Field(ge=0, le=10000)
    firstMismatch: dict | None
    mismatches: list[dict]
    comparisons: list[dict]

    @model_validator(mode="after")
    def bounded_report(self):
        if self.range.maximum - self.range.minimum + 1 != self.checkedCount:
            raise ValueError("Report range and checked count disagree.")
        if len(self.comparisons) != self.checkedCount or len(self.mismatches) != self.mismatchCount:
            raise ValueError("Report counts and recorded results disagree.")
        return self


def replay_report(data: dict) -> list[str]:
    report = ReplayRequest.model_validate(data)
    case = get_case(report.caseId)
    if not case.minimum <= report.range.minimum <= report.range.maximum <= case.maximum:
        raise ValueError("Report range is outside the registered case's domain.")
    actual = run_case(case, report.range.minimum, report.range.maximum, report.portVersion)
    # Compare the entire recorded evidence; the timestamp changes on every run.
    fields = (
        "manifest", "sourceHashes", "runtime", "checkedCount", "mismatchCount",
        "firstMismatch", "mismatches", "comparisons",
    )
    return [field for field in fields if actual[field] != getattr(report, field)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="JSON report downloaded from the workbench")
    args = parser.parse_args()
    try:
        if args.report.stat().st_size > 20_000_000:
            raise ValueError("Report is too large. Maximum size is 20 MB.")
        data = json.loads(args.report.read_text())
        differences = replay_report(data)
    except (OSError, ValueError, TypeError, ValidationError, ManifestError, InterpreterError) as error:
        print(f"Replay failed: {error}", file=sys.stderr)
        return 2
    if differences:
        print("Reproduction differs in " + ", ".join(differences) + ".", file=sys.stderr)
        return 1
    print("Reproduced source hashes and all recorded results.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
