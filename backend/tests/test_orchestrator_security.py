from __future__ import annotations

import pytest

from orchestrator import ConsensusOrchestrator


def _build_orchestrator(monkeypatch: pytest.MonkeyPatch) -> ConsensusOrchestrator:
    # Keep tests hermetic: skip live brain initialization.
    monkeypatch.setattr(ConsensusOrchestrator, "_initialize_brains", lambda self: None)
    return ConsensusOrchestrator()


def test_high_risk_majority_blocked_by_conflicting_high_risk_dissenter(monkeypatch):
    orchestrator = _build_orchestrator(monkeypatch)
    decision = orchestrator.evaluate_consensus(
        {"action": "PROPOSE", "message": "a"},
        {"action": "PROPOSE", "message": "b"},
        {"action": "REJECT", "message": "conflict"},
    )
    assert decision is None


def test_soft_consensus_accepts_low_risk_when_no_high_risk(monkeypatch):
    orchestrator = _build_orchestrator(monkeypatch)
    decision = orchestrator.evaluate_consensus(
        {"action": "REPLY", "message": "ok"},
        {"error": "timeout", "action": "NONE"},
        {"action": "MONITOR", "message": "watch"},
    )
    assert decision is not None
    assert decision["action"] in {"REPLY", "MONITOR"}


def test_fail_closed_on_no_consensus_for_high_risk(monkeypatch):
    orchestrator = _build_orchestrator(monkeypatch)
    decision = orchestrator.evaluate_consensus(
        {"action": "PROPOSE", "message": "a"},
        {"action": "REJECT", "message": "b"},
        {"action": "CANCEL", "message": "c"},
    )
    assert decision is None


def test_extract_json_object_accepts_code_fenced_json(monkeypatch):
    orchestrator = _build_orchestrator(monkeypatch)
    parsed = orchestrator._extract_json_object(
        "```json\n{\"action\":\"REPLY\",\"message\":\"ok\"}\n```",
        "test",
    )
    assert parsed["action"] == "REPLY"


def test_extract_json_object_rejects_non_object_json(monkeypatch):
    orchestrator = _build_orchestrator(monkeypatch)
    with pytest.raises(Exception):
        orchestrator._extract_json_object("[1,2,3]", "test")
