import logging

from agents.models import AgentProfile, AgentState  # noqa: F401

logger = logging.getLogger(__name__)


class StateManager:
    """
    Tracks mutable simulation state: agent stances, emotions, trust edges.

    Default trust between any two agents is 0.5 (neutral), not 0.
    Trust range: [0.0, 1.0] where 0=adversarial, 0.5=neutral, 1.0=full trust.
    """

    def __init__(self) -> None:
        self._states: dict[str, AgentState] = {}
        self._trust: dict[tuple[str, str], float] = {}

    def init_agent_state(self, agent_id: str) -> AgentState:
        state = AgentState(agent_id=agent_id)
        self._states[agent_id] = state
        return state

    def get_state(self, agent_id: str) -> AgentState:
        return self._states[agent_id]

    def update_state(self, state: AgentState) -> None:
        self._states[state.agent_id] = state

    def get_all_states(self) -> list[AgentState]:
        return list(self._states.values())

    def get_trust(self, agent_a_id: str, agent_b_id: str) -> float:
        return self._trust.get((agent_a_id, agent_b_id), 0.5)

    def update_trust(self, agent_a_id: str, agent_b_id: str, delta: float) -> None:
        if agent_a_id == agent_b_id:
            raise ValueError(f"Cannot set self-trust for agent {agent_a_id!r}")
        key = (agent_a_id, agent_b_id)
        current = self._trust.get(key, 0.5)
        self._trust[key] = max(0.0, min(1.0, current + delta))

    def get_all_trust(self) -> dict[tuple[str, str], float]:
        return dict(self._trust)
