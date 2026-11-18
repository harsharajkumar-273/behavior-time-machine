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
    assert {key: value for key, value in response.json().items() if key != "report"} == {
        "input": 4,
        "daysOverdue": 4,
        "legacyCents": 100,
        "modernCents": 25,
        "matches": False,
        "legacyOutput": "100",
        "policyLines": ["1010 Y = 0", "1020 IF X > 3 THEN Y = 25 * X", "1030 IF Y > 1000 THEN Y = 1000", "1040 PRINT Y"],
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
    assert response.json()["checkedCount"] == 366
    assert response.json()["mismatchCount"] == 0
    assert response.json()["firstMismatch"] is None


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


def test_transit_threshold_and_corrected_parity():
    initial = client.post("/api/sweep", json={"caseId": "transit", "portVersion": "flawed"}).json()
    assert initial["checkedCount"] == 101
    assert initial["mismatchCount"] == 1
    assert initial["firstMismatch"]["input"] == 65
    assert initial["firstMismatch"]["legacyCents"] == 100
    assert initial["firstMismatch"]["modernCents"] == 200
    corrected = client.post("/api/sweep", json={"caseId": "transit", "portVersion": "corrected"}).json()
    assert corrected["checkedCount"] == 101
    assert corrected["mismatches"] == []


def test_reports_include_source_hashes_and_all_mismatches():
    import hashlib
    from backend.contracts import ROOT
    report = client.post("/api/sweep", json={"portVersion": "flawed"}).json()
    assert [row["input"] for row in report["mismatches"]] == list(range(4, 43))
    assert report["sourceHashes"]["basic"] == hashlib.sha256((ROOT / "overdue.bas").read_bytes()).hexdigest()
    assert report["sourceHashes"]["port"] == hashlib.sha256((ROOT / "fees.py").read_bytes()).hexdigest()
    assert len(report["comparisons"]) == 366
    assert "expected" not in report["manifest"]


@pytest.mark.parametrize("output", ["", "100\n200\n", "100\n\n", "100.0\n", "FEE=100\n"])
def test_strict_integer_output(monkeypatch, output):
    monkeypatch.setattr("backend.runtime.subprocess.run", lambda *args, **kwargs:
        subprocess.CompletedProcess("pcbasic", 0, stdout=output, stderr=""))
    response = client.post("/api/compare", json={"caseId": "transit", "input": 65, "portVersion": "corrected"})
    assert response.status_code == 503


def test_unknown_manifest_is_distinct_from_execution_error():
    response = client.post("/api/sweep", json={"caseId": "unknown", "portVersion": "corrected"})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_manifest"


@pytest.mark.parametrize(("lower", "upper"), [(0, 10000), (10, 9), (False, 10), (0.5, 10)])
def test_manifest_bounds(lower, upper):
    from backend.contracts import Case, get_case
    from pydantic import ValidationError
    manifest = get_case("library").model_dump()
    manifest.update(minimum=lower, maximum=upper)
    with pytest.raises(ValidationError):
        Case.model_validate(manifest)


def test_compare_and_sweep_use_same_batch_execution(monkeypatch):
    from backend import runtime
    calls = []
    original = runtime.subprocess.run

    def record(*args, **kwargs):
        calls.append(kwargs["input"])
        return original(*args, **kwargs)

    monkeypatch.setattr(runtime.subprocess, "run", record)
    one = client.post("/api/compare", json={"caseId": "transit", "input": 65, "portVersion": "flawed"}).json()
    many = client.post("/api/sweep", json={"caseId": "transit", "portVersion": "flawed"}).json()
    assert len(calls) == 2
    assert one["legacyCents"] == many["firstMismatch"]["legacyCents"]
    assert one["report"]["range"] == {"minimum": 65, "maximum": 65}


def test_replay_reproduces_report_and_detects_edits():
    import copy
    from backend.replay import replay_report
    report = client.post("/api/compare", json={"caseId": "transit", "input": 65, "portVersion": "flawed"}).json()["report"]
    assert replay_report(report) == []
    changed_hash = copy.deepcopy(report)
    changed_hash["sourceHashes"]["basic"] = "0" * 64
    assert "sourceHashes" in replay_report(changed_hash)
    changed_output = copy.deepcopy(report)
    changed_output["comparisons"][0]["legacyCents"] = 200
    assert "comparisons" in replay_report(changed_output)


def test_replay_rejects_invalid_domain_before_execution(monkeypatch):
    from backend.replay import replay_report
    from pydantic import ValidationError
    report = client.post("/api/compare", json={"caseId": "transit", "input": 65, "portVersion": "flawed"}).json()["report"]
    report["range"] = {"minimum": 0, "maximum": 100000}
    monkeypatch.setattr("backend.replay.run_case", lambda *args: pytest.fail("Invalid report must not execute"))
    with pytest.raises(ValidationError):
        replay_report(report)
