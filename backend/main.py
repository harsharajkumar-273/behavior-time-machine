from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .contracts import ManifestError, get_case, load_cases
from .fees import PortVersion
from .runtime import InterpreterError, run_case

app = FastAPI(title="Behavior Time Machine")


class SweepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    portVersion: PortVersion
    caseId: str = "library"


class CompareRequest(SweepRequest):
    input: int | None = Field(default=None, strict=True)
    daysOverdue: int | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def require_input(self):
        if self.input is None and self.daysOverdue is None:
            raise ValueError("An integer input is required.")
        if self.input is not None and self.daysOverdue is not None and self.input != self.daysOverdue:
            raise ValueError("Conflicting inputs.")
        return self


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, error: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "invalid_input", "message": "Use a whole number within the selected case's range and a valid port version."})


@app.exception_handler(ManifestError)
async def invalid_manifest(request: Request, error: ManifestError):
    return JSONResponse(status_code=422, content={"error": "invalid_manifest", "message": str(error)})


@app.exception_handler(InterpreterError)
async def runtime_failure(request: Request, error: InterpreterError):
    return JSONResponse(status_code=503, content={"error": "runtime_error", "message": str(error)})


@app.get("/api/cases")
def cases():
    return [case.model_dump() for case in load_cases()]


@app.post("/api/compare")
def compare(body: CompareRequest):
    case = get_case(body.caseId)
    value = body.input if body.input is not None else body.daysOverdue
    if not case.minimum <= value <= case.maximum:
        return JSONResponse(status_code=422, content={"error": "invalid_input", "message": f"Use a whole number from {case.minimum} to {case.maximum}."})
    report = run_case(case, value, value, body.portVersion)
    return {**report["comparisons"][0], "report": report}


@app.post("/api/sweep")
def sweep(body: SweepRequest):
    case = get_case(body.caseId)
    return run_case(case, case.minimum, case.maximum, body.portVersion)


dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist.is_dir():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
