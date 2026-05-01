from agents.models import AgentState


class StateManager:
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
        key = (agent_a_id, agent_b_id)
        current = self._trust.get(key, 0.5)
        self._trust[key] = max(0.0, min(1.0, current + delta))
