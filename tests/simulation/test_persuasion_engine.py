import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from simulation.persuasion_engine import resolve_persuasion
from agents.generator import generate_agents
from agents.models import AgentState, RoundAction


def _make_action(agent_id, confidence=0.8):
    return RoundAction(
        agent_id=agent_id, name="Test", archetype="TruthSeeker",
        action="debate", target_id="target", free_text="I argue...",
        stance=0.8, emotion="determined", confidence=confidence,
    )


def test_returns_float():
    agents = generate_agents(count=2, seed=1)
    actor, target = agents[0], agents[1]
    actor_state = AgentState(agent_id=actor.id, stance=0.9, emotion="determined")
    target_state = AgentState(agent_id=target.id, stance=0.3, emotion="neutral")
    action = _make_action(actor.id)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=0.7, social_proof=0.6, repetition_bonus=0.1)
    assert isinstance(delta, float)


def test_hard_cap_015():
    """Max stance delta per round must not exceed 0.15."""
    agents = generate_agents(count=2, seed=1)
    actor, target = agents[0], agents[1]
    target_tv = target.trait_vector.model_copy(update={"moral_rigidity": 0.0, "susceptibility": 1.0})
    target = target.model_copy(update={"trait_vector": target_tv})

    actor_state = AgentState(agent_id=actor.id, stance=1.0, emotion="passionate", confidence=1.0)
    target_state = AgentState(agent_id=target.id, stance=0.0)
    action = _make_action(actor.id, confidence=1.0)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=1.0, social_proof=1.0, repetition_bonus=0.3)
    assert abs(delta) <= 0.15


def test_high_moral_rigidity_caps_at_002():
    """Moral rigidity >= 0.9 → max delta 0.02."""
    agents = generate_agents(count=2, seed=1)
    actor, target = agents[0], agents[1]
    target_tv = target.trait_vector.model_copy(update={"moral_rigidity": 0.95})
    target = target.model_copy(update={"trait_vector": target_tv})

    actor_state = AgentState(agent_id=actor.id, stance=1.0, emotion="passionate")
    target_state = AgentState(agent_id=target.id, stance=0.0)
    action = _make_action(actor.id, confidence=1.0)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=1.0, social_proof=1.0, repetition_bonus=0.3)
    assert abs(delta) <= 0.02


def test_zero_delta_when_low_trust_and_low_susceptibility():
    agents = generate_agents(count=2, seed=5)
    actor, target = agents[0], agents[1]
    target_tv = target.trait_vector.model_copy(update={"susceptibility": 0.0, "moral_rigidity": 0.9})
    target = target.model_copy(update={"trait_vector": target_tv})

    actor_state = AgentState(agent_id=actor.id, stance=0.9)
    target_state = AgentState(agent_id=target.id, stance=0.5, confidence=0.9)
    action = _make_action(actor.id, confidence=0.1)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=0.1, social_proof=0.1, repetition_bonus=0.0)
    assert delta == 0.0


def test_delta_direction_moves_toward_actor_stance():
    agents = generate_agents(count=2, seed=3)
    actor, target = agents[0], agents[1]
    actor_state = AgentState(agent_id=actor.id, stance=0.9, emotion="optimistic")
    target_state = AgentState(agent_id=target.id, stance=0.1, confidence=0.3)
    target_tv = target.trait_vector.model_copy(update={"moral_rigidity": 0.0, "susceptibility": 0.9})
    target = target.model_copy(update={"trait_vector": target_tv})
    action = _make_action(actor.id, confidence=0.9)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=0.8, social_proof=0.7, repetition_bonus=0.2)
    assert delta >= 0
