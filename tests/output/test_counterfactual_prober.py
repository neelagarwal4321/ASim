import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from agents.models import AgentProfile, AgentState, TraitVector
from output.aggregator import compute_verdict
from output.counterfactual_prober import run_probes


def _trait() -> TraitVector:
    return TraitVector(
        openness=0.5, conscientiousness=0.5, extraversion=0.5,
        agreeableness=0.5, neuroticism=0.5, moral_rigidity=0.5, susceptibility=0.5,
    )


def _agent(i: int, archetype: str = "Pragmatist") -> AgentProfile:
    return AgentProfile(
        id=str(i), name=f"A{i}", archetype=archetype, trait_vector=_trait(),
        core_beliefs=[], voice_style="plain", moral_alignment="utilitarian", appeal_type="rational",
    )


def _state(i: int, stance: float) -> AgentState:
    return AgentState(agent_id=str(i), stance=stance)


def test_empty_returns_empty():
    assert run_probes([], [], {"avg_stance": 0.5}) == []


def test_baseline_probes_always_emit_two():
    agents = [_agent(i) for i in range(4)]
    states = [_state(i, s) for i, s in enumerate([0.7, 0.8, 0.2, 0.3])]
    baseline = compute_verdict(states)
    probes = run_probes(states, agents, baseline)
    levers = [p["lever"] for p in probes]
    assert "low_rigidity_population" in levers
    assert "amplified_polarization" in levers


def test_manipulator_probe_when_archetype_present():
    agents = [_agent(0, "Manipulator"), _agent(1, "Pragmatist"), _agent(2, "Idealist")]
    states = [_state(0, 0.9), _state(1, 0.4), _state(2, 0.3)]
    baseline = compute_verdict(states)
    probes = run_probes(states, agents, baseline)
    levers = [p["lever"] for p in probes]
    assert "no_manipulators" in levers
    cf = next(p for p in probes if p["lever"] == "no_manipulators")
    assert "verdict" in cf and "explanation" in cf


def test_manipulator_probe_absent_when_no_manipulator():
    agents = [_agent(i) for i in range(3)]
    states = [_state(i, 0.6) for i in range(3)]
    baseline = compute_verdict(states)
    probes = run_probes(states, agents, baseline)
    assert all(p["lever"] != "no_manipulators" for p in probes)


def test_probe_shape_is_serializable():
    agents = [_agent(i) for i in range(3)]
    states = [_state(i, 0.5 + 0.1 * i) for i in range(3)]
    baseline = compute_verdict(states)
    probes = run_probes(states, agents, baseline)
    for p in probes:
        assert isinstance(p["verdict"], str)
        assert 0.0 <= p["confidence"] <= 1.0
        assert set(p["distribution"].keys()) == {"support", "oppose", "undecided"}
        assert isinstance(p["avg_stance_delta"], float)
        assert p["magnitude"] in {"negligible", "minor", "moderate", "large"}
