import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from agents.models import AgentProfile, AgentState, RoundAction, TraitVector
from simulation.round_log_builder import build_round_log


def _trait() -> TraitVector:
    return TraitVector(
        openness=0.5, conscientiousness=0.5, extraversion=0.5,
        agreeableness=0.5, neuroticism=0.5, moral_rigidity=0.5, susceptibility=0.5,
    )


def _agent(i: int) -> AgentProfile:
    return AgentProfile(
        id=str(i), name=f"A{i}", archetype="Pragmatist",
        trait_vector=_trait(), core_beliefs=[],
        voice_style="plain", moral_alignment="utilitarian", appeal_type="rational",
    )


def _state(i: int, stance: float = 0.5, influence: float = 0.1) -> AgentState:
    return AgentState(agent_id=str(i), stance=stance, influence_score=influence, interaction_count=1)


def _action(i: int, stance: float = 0.5) -> RoundAction:
    return RoundAction(
        agent_id=str(i), name=f"A{i}", archetype="Pragmatist",
        action="debate", target_id=None, free_text=f"agent {i} speaks",
        stance=stance, emotion="neutral", confidence=0.5, argument_quality=0.5,
    )


def test_envelope_shape_matches_frontend_contract():
    agents = [_agent(0), _agent(1)]
    states = [_state(0, 0.7), _state(1, 0.3)]
    actions = [_action(0, 0.7), _action(1, 0.3)]
    env = build_round_log(
        simulation_id="sim-1", round_num=2, total_rounds=5,
        actions=actions, states=states, agents=agents, archetype_colors={},
        distribution={"support": 0.5, "oppose": 0.5, "undecided": 0.0},
        cumulative_interactions=4, cumulative_events=0,
        prev_cohesion=None, prev_entropy=None,
    )
    assert env["type"] == "round_log"
    payload = env["payload"]
    assert payload["simulation_id"] == "sim-1"
    assert payload["round"] == 2
    assert payload["total_rounds"] == 5
    assert len(payload["agents"]) == 2
    assert {"id", "name", "archetype", "stance", "emotion", "action", "message", "influence", "community_id"} <= set(payload["agents"][0].keys())
    assert payload["communities"] == []
    assert payload["edges"] == []
    assert payload["events"] == []
    assert {"cohesion", "cohesion_delta", "entropy", "entropy_delta",
            "interactions_this_round", "total_interactions",
            "avg_response_ms", "total_events"} <= set(payload["metrics"].keys())
    assert len(payload["outcomes"]) == 3


def test_cohesion_high_when_stances_clustered():
    agents = [_agent(i) for i in range(4)]
    states = [_state(i, 0.5) for i in range(4)]
    actions = [_action(i, 0.5) for i in range(4)]
    env = build_round_log(
        simulation_id="s", round_num=1, total_rounds=1,
        actions=actions, states=states, agents=agents, archetype_colors={},
        distribution={"support": 0.0, "oppose": 0.0, "undecided": 1.0},
        cumulative_interactions=4, cumulative_events=0,
        prev_cohesion=None, prev_entropy=None,
    )
    assert env["payload"]["metrics"]["cohesion"] == 1.0


def test_cohesion_drops_when_split():
    agents = [_agent(i) for i in range(4)]
    states = [_state(0, 0.0), _state(1, 0.0), _state(2, 1.0), _state(3, 1.0)]
    actions = [_action(i, states[i].stance) for i in range(4)]
    env = build_round_log(
        simulation_id="s", round_num=1, total_rounds=1,
        actions=actions, states=states, agents=agents, archetype_colors={},
        distribution={"support": 0.5, "oppose": 0.5, "undecided": 0.0},
        cumulative_interactions=4, cumulative_events=0,
        prev_cohesion=None, prev_entropy=None,
    )
    assert env["payload"]["metrics"]["cohesion"] == 0.0


def test_deltas_use_prev_values():
    agents = [_agent(0)]
    states = [_state(0, 0.5)]
    actions = [_action(0, 0.5)]
    env = build_round_log(
        simulation_id="s", round_num=2, total_rounds=5,
        actions=actions, states=states, agents=agents, archetype_colors={},
        distribution={"support": 0.5, "oppose": 0.5, "undecided": 0.0},
        cumulative_interactions=2, cumulative_events=0,
        prev_cohesion=0.8, prev_entropy=0.5,
    )
    metrics = env["payload"]["metrics"]
    assert metrics["cohesion_delta"] == round(metrics["cohesion"] - 0.8, 4)
    assert metrics["entropy_delta"] == round(metrics["entropy"] - 0.5, 4)
