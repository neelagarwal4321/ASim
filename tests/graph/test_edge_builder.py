import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from agents.models import AgentProfile, TraitVector
from graph.edge_builder import build_edges, MAX_EDGES


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


def test_no_trust_no_edges():
    assert build_edges([_agent(0), _agent(1)], {}) == []


def test_neutral_trust_filtered_out():
    edges = build_edges([_agent(0), _agent(1)], {("0", "1"): 0.5})
    assert edges == []


def test_high_trust_emits_positive_edge():
    edges = build_edges([_agent(0), _agent(1)], {("0", "1"): 0.8})
    assert len(edges) == 1
    assert edges[0]["type"] == "positive"
    assert edges[0]["source"] == "0"
    assert edges[0]["target"] == "1"
    assert 0.0 <= edges[0]["strength"] <= 1.0


def test_low_trust_emits_hostile_edge():
    edges = build_edges([_agent(0), _agent(1)], {("0", "1"): 0.2})
    assert len(edges) == 1
    assert edges[0]["type"] == "hostile"


def test_manipulator_mid_trust_emits_covert_edge():
    edges = build_edges([_agent(0, "Manipulator"), _agent(1)], {("0", "1"): 0.5})
    assert len(edges) == 1
    assert edges[0]["type"] == "covert"


def test_max_edges_cap_keeps_strongest():
    agents = [_agent(i) for i in range(MAX_EDGES + 50)]
    trust = {}
    # Weak positives below cap...
    for i in range(MAX_EDGES + 30):
        trust[(str(i), str((i + 1) % len(agents)))] = 0.65
    # ...and a few strong ones above.
    for i in range(5):
        trust[(f"strong{i}_src", f"strong{i}_dst")] = 0.99  # unknown ids dropped
    trust[("0", "1")] = 0.99  # overwrite to a known-strong pair
    edges = build_edges(agents, trust)
    assert len(edges) <= MAX_EDGES
    # Strongest edge should be present.
    assert any(e["source"] == "0" and e["target"] == "1" for e in edges)


def test_unknown_agent_ids_filtered_out():
    edges = build_edges([_agent(0)], {("0", "ghost"): 0.9, ("ghost", "0"): 0.9})
    assert edges == []
