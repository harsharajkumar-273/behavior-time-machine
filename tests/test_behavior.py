import subprocess

import pytest
from fastapi.testclient import TestClient

from backend.fees import calculate_fee
from backend.main import app
from backend.runtime import run_basic

client = TestClient(app)


def test_basic_policy_boundaries():
    assert run_basic([0, 3, 4, 39, 40, 365]) == [0, 0, 100, 975, 1000, 1000]


def test_fee_at_4_days():
    assert calculate_fee(4, "corrected") == 100


def test_compare_shows_observed_evidence():
    grace = client.post("/api/compare", json={"daysOverdue": 3, "portVersion": "flawed"})
    assert grace.json()["matches"] is True
    response = client.post("/api/compare", json={"daysOverdue": 4, "portVersion": "flawed"})
    assert response.status_code == 200
    assert response.json() == {
        "daysOverdue": 4,
        "legacyCents": 100,
        "modernCents": 25,
        "matches": False,
        "legacyOutput": "FEE= 100",
        "policyLines": ["40 F = 0", "50 IF D > 3 THEN F = 25 * D", "60 IF F > 1000 THEN F = 1000"],
    }


def test_initial_sweep_finds_smallest_difference():
    response = client.post("/api/sweep", json={"portVersion": "flawed"})
    assert response.status_code == 200
    data = response.json()
    assert data["checkedCount"] == 366
    assert data["mismatchCount"] == 39
    assert data["firstMismatch"]["daysOverdue"] == 4


def test_corrected_sweep_verifies_all_supported_inputs():
    response = client.post("/api/sweep", json={"portVersion": "corrected"})
    assert response.status_code == 200
    assert response.json() == {"checkedCount": 366, "mismatchCount": 0, "firstMismatch": None}


@pytest.mark.parametrize("invalid", [-1, 0.5, 366, True, "4", None])
def test_comparison_rejects_invalid_days(invalid):
    response = client.post("/api/compare", json={"daysOverdue": invalid, "portVersion": "flawed"})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_input"


@pytest.mark.parametrize(("path", "body"), [
    ("/api/compare", {"portVersion": "flawed"}),
    ("/api/sweep", {"portVersion": "unknown"}),
])
def test_required_fields_and_variants(path, body):
    response = client.post(path, json=body)
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_input"


@pytest.mark.parametrize("failure", [
    FileNotFoundError(),
    subprocess.TimeoutExpired("pcbasic", 8),
    subprocess.CompletedProcess("pcbasic", 1, stdout="", stderr="unavailable"),
    subprocess.CompletedProcess("pcbasic", 0, stdout="? 1\n? 4\nFEE= unclear\n", stderr=""),
])
def test_runtime_failures_never_report_parity(monkeypatch, failure):
    def failed_run(*args, **kwargs):
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr("backend.runtime.subprocess.run", failed_run)
    response = client.post("/api/compare", json={"daysOverdue": 4, "portVersion": "corrected"})
    assert response.status_code == 503
    assert response.json()["error"] == "runtime_error"
    assert "matches" not in response.json()
