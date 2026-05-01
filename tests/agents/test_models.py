import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import pytest
from pydantic import ValidationError
from agents.models import TraitVector, AgentProfile, AgentState, RoundAction


def test_trait_vector_clamps_to_range():
    with pytest.raises(ValidationError):
        TraitVector(openness=1.5, conscientiousness=0.5, extraversion=0.5,
                    agreeableness=0.5, neuroticism=0.5, moral_rigidity=0.5, susceptibility=0.5)


def test_agent_profile_valid():
    tv = TraitVector(openness=0.7, conscientiousness=0.6, extraversion=0.5,
                     agreeableness=0.4, neuroticism=0.3, moral_rigidity=0.2, susceptibility=0.5)
    agent = AgentProfile(
        id="abc",
        name="Alice",
        archetype="TruthSeeker",
        trait_vector=tv,
        core_beliefs=["Facts matter"],
        voice_style="precise and analytical",
        moral_alignment="utilitarian",
        appeal_type="rational",
    )
    assert agent.name == "Alice"
    assert agent.moral_alignment == "utilitarian"


def test_agent_state_defaults():
    state = AgentState(agent_id="abc")
    assert state.stance == 0.5
    assert state.emotion == "neutral"
    assert state.round == 0


def test_agent_state_stance_clamped():
    with pytest.raises(ValidationError):
        AgentState(agent_id="abc", stance=1.5)


def test_round_action_valid():
    action = RoundAction(
        agent_id="abc", name="Alice", archetype="TruthSeeker",
        action="debate", target_id="xyz", free_text="I disagree.",
        stance=0.3, emotion="angry", confidence=0.7,
    )
    assert action.action == "debate"
