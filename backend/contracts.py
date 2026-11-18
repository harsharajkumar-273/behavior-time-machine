import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

ROOT = Path(__file__).parent
MAX_RANGE_SIZE = 10_000


class ManifestError(Exception):
    pass


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    title: str
    basicFile: str = Field(pattern=r"^[a-z][a-z0-9_]*\.bas$")
    portFile: str = Field(pattern=r"^[a-z][a-z0-9_]*\.py$")
    portFunction: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    minimum: int = Field(ge=-32768, le=32766)
    maximum: int = Field(ge=-32768, le=32766)
    parser: str = Field(pattern=r"^integer-lines$")
    inputLabel: str
    inputUnit: str
    outputUnit: str = Field(pattern=r"^(cents|integer)$")

    @model_validator(mode="after")
    def valid_range(self):
        if not 1 <= self.maximum - self.minimum + 1 <= MAX_RANGE_SIZE:
            raise ValueError("Range must contain between 1 and 10,000 integers.")
        return self


def load_cases() -> list[Case]:
    try:
        cases = [Case.model_validate(item) for item in json.loads((ROOT / "cases.json").read_text())]
        if not cases or len({case.id for case in cases}) != len(cases):
            raise ValueError("Case IDs must be unique.")
        for case in cases:
            if not (ROOT / case.basicFile).is_file() or not (ROOT / case.portFile).is_file():
                raise ValueError("A declared source file is missing.")
        return cases
    except (ValueError, TypeError, OSError, ValidationError) as error:
        raise ManifestError("The bundled case manifest is invalid.") from error


def get_case(case_id: str) -> Case:
    for case in load_cases():
        if case.id == case_id:
            return case
    raise ManifestError("Unknown migration case.")
