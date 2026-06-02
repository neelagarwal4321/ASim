import logging
import statistics
from agents.models import AgentProfile, AgentState, RelationshipEdge  # noqa: F401

logger = logging.getLogger(__name__)


class SimulationState:
    """In-memory simulation state — Phase 1. No DB."""

    def __init__(self, simulation_id: str, scenario: str, profiles: list[AgentProfile]) -> None:
        self.simulation_id = simulation_id
        self.scenario = scenario
        self._profiles: dict[str, AgentProfile] = {p.id: p for p in profiles}
        self._states: dict[str, AgentState] = {
            p.id: AgentState(agent_id=p.id, round=0)
            for p in profiles
        }
        agent_ids = list(self._profiles.keys())
        self._edges: dict[tuple[str, str], RelationshipEdge] = {
            (a, b): RelationshipEdge(from_agent=a, to_agent=b, trust_score=0.3)
            for a in agent_ids
            for b in agent_ids
            if a != b
        }
        self._round_history: list[dict] = []
        logger.info("SimulationState init: sim=%s agents=%d", simulation_id, len(profiles))

    def get_state(self, agent_id: str) -> AgentState:
        return self._states[agent_id]

    def update_state(self, agent_id: str, new_state: AgentState) -> None:
        self._states[agent_id] = new_state

    def get_profile(self, agent_id: str) -> AgentProfile:
        return self._profiles[agent_id]

    def get_edge(self, from_id: str, to_id: str) -> RelationshipEdge:
        return self._edges.get(
            (from_id, to_id),
            RelationshipEdge(from_agent=from_id, to_agent=to_id, trust_score=0.3),
        )

    def update_edge(self, edge: RelationshipEdge) -> None:
        self._edges[(edge.from_agent, edge.to_agent)] = edge

    def get_all_states(self) -> list[AgentState]:
        return list(self._states.values())

    def get_all_profiles(self) -> list[AgentProfile]:
        return list(self._profiles.values())

    def append_round_summary(self, summary: dict) -> None:
        self._round_history.append(summary)

    def get_round_summary(self, round_num: int) -> dict:
        stances = [s.stance for s in self._states.values()]
        mean_s = statistics.mean(stances) if stances else 0.5
        std_s = statistics.stdev(stances) if len(stances) > 1 else 0.0
        return {
            "round_num": round_num,
            "mean_stance": round(mean_s, 4),
            "std_stance": round(std_s, 4),
            "distribution": {
                "strongly_for": sum(1 for s in stances if s >= 0.65),
                "weakly_for": sum(1 for s in stances if 0.5 <= s < 0.65),
                "neutral": sum(1 for s in stances if 0.4 <= s < 0.5),
                "weakly_against": sum(1 for s in stances if 0.25 <= s < 0.4),
                "strongly_against": sum(1 for s in stances if s < 0.25),
            },
        }


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
        assert agent_a_id != agent_b_id, "Cannot set self-trust"
        key = (agent_a_id, agent_b_id)
        current = self._trust.get(key, 0.5)
        self._trust[key] = max(0.0, min(1.0, current + delta))

    def get_all_trust(self) -> dict[tuple[str, str], float]:
        return dict(self._trust)
