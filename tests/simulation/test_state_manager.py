import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from simulation.state_manager import StateManager
from agents.models import AgentState


def test_init_creates_default_state():
    mgr = StateManager()
    state = mgr.init_agent_state("agent-1")
    assert state.agent_id == "agent-1"
    assert state.stance == 0.5
    assert state.round == 0


def test_get_state_returns_stored():
    mgr = StateManager()
    mgr.init_agent_state("agent-1")
    state = mgr.get_state("agent-1")
    assert state.agent_id == "agent-1"


def test_update_state_persists():
    mgr = StateManager()
    state = mgr.init_agent_state("agent-1")
    state.stance = 0.9
    state.emotion = "angry"
    mgr.update_state(state)
    retrieved = mgr.get_state("agent-1")
    assert retrieved.stance == 0.9
    assert retrieved.emotion == "angry"


def test_get_all_states():
    mgr = StateManager()
    mgr.init_agent_state("a1")
    mgr.init_agent_state("a2")
    mgr.init_agent_state("a3")
    all_states = mgr.get_all_states()
    assert len(all_states) == 3


def test_trust_defaults_to_neutral():
    mgr = StateManager()
    trust = mgr.get_trust("a1", "a2")
    assert trust == 0.5


def test_trust_update_clamps():
    mgr = StateManager()
    mgr.update_trust("a1", "a2", 0.9)
    assert mgr.get_trust("a1", "a2") == 1.0
    mgr.update_trust("a1", "a2", -2.0)
    assert mgr.get_trust("a1", "a2") == 0.0
