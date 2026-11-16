from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .fees import MAX_DAYS, PortVersion, calculate_fee
from .runtime import POLICY_LINES, InterpreterError, run_basic

app = FastAPI(title="Behavior Time Machine")


class SweepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    portVersion: PortVersion


class CompareRequest(SweepRequest):
    daysOverdue: int = Field(strict=True, ge=0, le=MAX_DAYS)


@app.exception_handler(RequestValidationError)
async def invalid_input(request: Request, error: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "invalid_input", "message": "Use a whole number from 0 to 365 and select a valid port version."},
    )


@app.exception_handler(InterpreterError)
async def runtime_failure(request: Request, error: InterpreterError):
    return JSONResponse(status_code=503, content={"error": "runtime_error", "message": str(error)})


def compare_fee(days: int, legacy_cents: int, version: PortVersion):
    modern_cents = calculate_fee(days, version)
    return {
        "daysOverdue": days,
        "legacyCents": legacy_cents,
        "modernCents": modern_cents,
        "matches": legacy_cents == modern_cents,
        "legacyOutput": f"FEE= {legacy_cents}",
        "policyLines": POLICY_LINES,
    }


@app.post("/api/compare")
def compare(body: CompareRequest):
    days = body.daysOverdue
    return compare_fee(days, run_basic([days])[0], body.portVersion)


@app.post("/api/sweep")
def sweep(body: SweepRequest):
    days = list(range(MAX_DAYS + 1))
    mismatches = [
        (day, fee)
        for day, fee in zip(days, run_basic(days), strict=True)
        if calculate_fee(day, body.portVersion) != fee
    ]
    return {
        "checkedCount": len(days),
        "mismatchCount": len(mismatches),
        "firstMismatch": compare_fee(*mismatches[0], body.portVersion) if mismatches else None,
    }


dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist.is_dir():
    app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
