import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from agents.models import AgentProfile, AgentState, TraitVector
from graph.community_detector import detect_communities, MIN_COMMUNITY_SIZE


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


def test_empty_agents_returns_empty():
    assert detect_communities([], [], {}) == []


def test_single_stance_bucket_with_no_trust_still_clusters():
    agents = [_agent(i) for i in range(3)]
    states = [_state(i, 0.85) for i in range(3)]
    communities = detect_communities(agents, states, {})
    assert len(communities) == 1
    assert communities[0]["name"] == "Strong Support"
    assert set(communities[0]["member_ids"]) == {"0", "1", "2"}


def test_distinct_stance_buckets_become_distinct_communities():
    agents = [_agent(i) for i in range(4)]
    states = [_state(0, 0.05), _state(1, 0.10), _state(2, 0.85), _state(3, 0.90)]
    communities = detect_communities(agents, states, {})
    names = sorted(c["name"] for c in communities)
    assert names == ["Strong Oppose", "Strong Support"]
    for c in communities:
        assert len(c["member_ids"]) == 2


def test_small_community_dropped_under_min_size():
    # MIN_COMMUNITY_SIZE = 2, so a single-member bucket is dropped.
    assert MIN_COMMUNITY_SIZE == 2
    agents = [_agent(0)]
    states = [_state(0, 0.5)]
    communities = detect_communities(agents, states, {})
    assert communities == []


def test_high_trust_splits_within_bucket():
    # Both agents in Strong Support, but no trust between {0,1} and {2,3} -> trust forms two cliques.
    agents = [_agent(i) for i in range(4)]
    states = [_state(i, 0.9) for i in range(4)]
    trust = {
        ("0", "1"): 0.9,
        ("1", "0"): 0.9,
        ("2", "3"): 0.9,
        ("3", "2"): 0.9,
    }
    communities = detect_communities(agents, states, trust)
    assert len(communities) == 2
    member_sets = [set(c["member_ids"]) for c in communities]
    assert {"0", "1"} in member_sets
    assert {"2", "3"} in member_sets


def test_member_ids_are_unique_per_agent():
    agents = [_agent(i) for i in range(6)]
    states = [_state(i, 0.10 + 0.15 * i) for i in range(6)]
    communities = detect_communities(agents, states, {})
    all_members = [m for c in communities for m in c["member_ids"]]
    assert len(all_members) == len(set(all_members))
