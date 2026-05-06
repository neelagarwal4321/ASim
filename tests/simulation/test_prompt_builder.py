import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from simulation.prompt_builder import build_prompt
from agents.generator import generate_agents
from agents.models import AgentState


def _make_agent_and_state():
    agents = generate_agents(count=1, seed=42)
    agent = agents[0]
    state = AgentState(agent_id=agent.id, stance=0.4, emotion="angry", confidence=0.6)
    return agent, state


def test_returns_three_strings():
    agent, state = _make_agent_and_state()
    result = build_prompt(agent, state, "debate", None, "Test scenario", 1, {}, 5)
    assert len(result) == 3
    static_sys, dynamic_ctx, user_msg = result
    assert isinstance(static_sys, str)
    assert isinstance(dynamic_ctx, str)
    assert isinstance(user_msg, str)


def test_static_system_contains_identity():
    agent, state = _make_agent_and_state()
    static_sys, _, _ = build_prompt(agent, state, "debate", None, "Test scenario", 1, {}, 5)
    assert agent.name in static_sys
    assert agent.archetype in static_sys


def test_static_system_contains_moral_framing():
    agent, state = _make_agent_and_state()
    static_sys, _, _ = build_prompt(agent, state, "debate", None, "Test", 1, {}, 5)
    assert agent.moral_alignment in static_sys


def test_dynamic_context_contains_scenario():
    agent, state = _make_agent_and_state()
    _, dynamic_ctx, _ = build_prompt(agent, state, "debate", None, "Vaccine mandate test", 1, {}, 5)
    assert "Vaccine mandate test" in dynamic_ctx


def test_dynamic_context_contains_stance():
    agent, state = _make_agent_and_state()
    _, dynamic_ctx, _ = build_prompt(agent, state, "debate", None, "Test", 1, {}, 5)
    assert "0.4" in dynamic_ctx


def test_user_message_contains_action():
    agent, state = _make_agent_and_state()
    _, _, user_msg = build_prompt(agent, state, "challenge", "Bob", "Test", 1, {}, 5)
    assert "challenge" in user_msg
    assert "Bob" in user_msg


def test_user_message_ends_with_json_spec():
    agent, state = _make_agent_and_state()
    _, _, user_msg = build_prompt(agent, state, "debate", None, "Test", 1, {}, 5)
    assert '"action"' in user_msg
    assert '"stance"' in user_msg
    assert '"emotion"' in user_msg


def test_block_order_static_before_dynamic():
    agent, state = _make_agent_and_state()
    static_sys, dynamic_ctx, user_msg = build_prompt(
        agent, state, "debate", None, "Scenario X", 2, {}, 5
    )
    assert agent.name in static_sys
    assert str(agent.trait_vector.openness)[:3] in static_sys or "openness" in static_sys.lower()
    assert agent.moral_alignment in static_sys
    assert "Scenario X" in dynamic_ctx
    assert str(state.stance) in dynamic_ctx
    assert "debate" in user_msg
