import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from agents.models import AgentProfile, AgentState, TraitVector
from output.report_assembler import assemble


def _agent(i: int) -> AgentProfile:
    return AgentProfile(
        id=str(i), name=f"A{i}", archetype="Pragmatist",
        trait_vector=TraitVector(
            openness=0.5, conscientiousness=0.5, extraversion=0.5,
            agreeableness=0.5, neuroticism=0.5, moral_rigidity=0.5, susceptibility=0.5,
        ),
        core_beliefs=[], voice_style="plain", moral_alignment="utilitarian", appeal_type="rational",
    )


def _state(i: int, stance: float = 0.6, influence: float = 0.4) -> AgentState:
    return AgentState(agent_id=str(i), stance=stance, influence_score=influence, interaction_count=5)


def test_assemble_basic_shape():
    verdict = {"verdict": "consensus", "confidence": 0.7,
               "distribution": {"support": 0.6, "oppose": 0.3, "undecided": 0.1},
               "avg_stance": 0.62}
    top = [{"agent": _agent(0), "state": _state(0)}]
    report = assemble(
        scenario="Test", verdict=verdict, narrative="Story.",
        counterfactuals=[{"lever": "x"}], top_agents=top,
        round_count=5, agent_count=10,
    )
    assert report["scenario"] == "Test"
    assert report["verdict"] == "consensus"
    assert report["confidence"] == 0.7
    assert report["narrative"] == "Story."
    assert report["round_count"] == 5
    assert report["agent_count"] == 10
    assert report["counterfactuals"] == [{"lever": "x"}]


def test_top_agents_flattened():
    verdict = {"verdict": "x", "confidence": 0.5, "distribution": {"support": 0.5, "oppose": 0.5, "undecided": 0.0},
               "avg_stance": 0.5}
    top = [{"agent": _agent(7), "state": _state(7, stance=0.81, influence=0.42)}]
    report = assemble(
        scenario="S", verdict=verdict, narrative="n", counterfactuals=[],
        top_agents=top, round_count=3, agent_count=1,
    )
    ta = report["top_agents"][0]
    assert ta["id"] == "7"
    assert ta["name"] == "A7"
    assert ta["final_stance"] == 0.81
    assert ta["influence_score"] == 0.42
    assert ta["interaction_count"] == 5
    assert ta["moral_alignment"] == "utilitarian"


def test_assemble_empty_top_agents():
    verdict = {"verdict": "x", "confidence": 0.5,
               "distribution": {"support": 0.5, "oppose": 0.5, "undecided": 0.0}, "avg_stance": 0.5}
    report = assemble(
        scenario="S", verdict=verdict, narrative="n", counterfactuals=[],
        top_agents=[], round_count=0, agent_count=0,
    )
    assert report["top_agents"] == []
