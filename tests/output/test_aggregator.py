import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from output.aggregator import compute_verdict
from agents.models import AgentState


def _make_states(stances: list[float]) -> list[AgentState]:
    return [AgentState(agent_id=str(i), stance=s) for i, s in enumerate(stances)]


def test_majority_support():
    states = _make_states([0.8, 0.7, 0.9, 0.75, 0.3, 0.2])
    result = compute_verdict(states)
    assert result["confidence"] > 0
    assert "support" in result["verdict"].lower() or "consensus" in result["verdict"].lower()


def test_majority_oppose():
    states = _make_states([0.1, 0.2, 0.15, 0.3, 0.8, 0.25])
    result = compute_verdict(states)
    assert "reject" in result["verdict"].lower() or "opposition" in result["verdict"].lower() or "oppose" in result["verdict"].lower()


def test_returns_distribution():
    states = _make_states([0.8, 0.8, 0.2, 0.2, 0.5, 0.5])
    result = compute_verdict(states)
    assert "support" in result["distribution"]
    assert "oppose" in result["distribution"]
    assert "undecided" in result["distribution"]
    total = result["distribution"]["support"] + result["distribution"]["oppose"] + result["distribution"]["undecided"]
    assert abs(total - 1.0) < 0.01


def test_empty_states():
    result = compute_verdict([])
    assert result["confidence"] == 0.0


def test_confidence_is_float_between_0_and_1():
    states = _make_states([0.7, 0.8, 0.6, 0.9, 0.3, 0.2])
    result = compute_verdict(states)
    assert 0.0 <= result["confidence"] <= 1.0
