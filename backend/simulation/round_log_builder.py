"""
Build the WS `round_log` payload the frontend renders on the LiveSimulation
page. The frontend contract lives in frontend/src/types/wsMessages.ts and is
the single source of truth for field names.

This module is intentionally separate from the orchestrator so the network
shape can evolve without touching the simulation loop.
"""

from __future__ import annotations

import math

from agents.models import AgentProfile, AgentState, RoundAction
from graph.community_detector import detect_communities
from graph.edge_builder import build_edges

# Outcome palette mirrors the frontend RoundLogOutcome colors.
_OUTCOME_PALETTE = {
    "Support": "var(--state-success)",
    "Oppose": "var(--state-error)",
    "Undecided": "var(--text-secondary)",
}


def _shannon_entropy(values: list[float]) -> float:
    total = 0.0
    for p in values:
        if p > 0:
            total -= p * math.log2(p)
    # Max entropy for 3-class distribution is log2(3) ~ 1.585
    return round(total / math.log2(3), 4) if total else 0.0


def _cohesion(stances: list[float]) -> float:
    """1 - normalised std-dev. 1.0 = everyone agrees, 0.0 = maximum spread."""
    if len(stances) <= 1:
        return 1.0
    mean = sum(stances) / len(stances)
    var = sum((s - mean) ** 2 for s in stances) / len(stances)
    std = math.sqrt(var)
    # Std-dev on [0,1] caps at 0.5 (when half at 0, half at 1).
    return round(max(0.0, 1.0 - std / 0.5), 4)


def build_round_log(
    *,
    simulation_id: str,
    round_num: int,
    total_rounds: int,
    actions: list[RoundAction],
    states: list[AgentState],
    agents: list[AgentProfile],
    archetype_colors: dict[str, str],
    distribution: dict,
    cumulative_interactions: int,
    cumulative_events: int,
    prev_cohesion: float | None,
    prev_entropy: float | None,
    trust: dict[tuple[str, str], float] | None = None,
    avg_response_ms: float = 0.0,
) -> dict:
    profile_by_id = {a.id: a for a in agents}
    state_by_id = {s.agent_id: s for s in states}
    trust = trust or {}

    communities = detect_communities(agents, states, trust)
    community_of: dict[str, str] = {}
    for community in communities:
        for member_id in community["member_ids"]:
            community_of[member_id] = community["id"]
    edges = build_edges(agents, trust)

    agents_payload = []
    for action in actions:
        profile = profile_by_id.get(action.agent_id)
        state = state_by_id.get(action.agent_id)
        if profile is None or state is None:
            continue
        agents_payload.append({
            "id": action.agent_id,
            "name": action.name,
            "archetype": action.archetype,
            "stance": round(action.stance, 3),
            "emotion": action.emotion,
            "action": action.action,
            "message": action.free_text,
            "influence": round(state.influence_score, 3),
            "community_id": community_of.get(action.agent_id, ""),
        })

    stances = [s.stance for s in states]
    cohesion = _cohesion(stances)
    entropy = _shannon_entropy([
        distribution.get("support", 0.0),
        distribution.get("oppose", 0.0),
        distribution.get("undecided", 0.0),
    ])

    metrics = {
        "cohesion": cohesion,
        "cohesion_delta": round(cohesion - (prev_cohesion if prev_cohesion is not None else cohesion), 4),
        "entropy": entropy,
        "entropy_delta": round(entropy - (prev_entropy if prev_entropy is not None else entropy), 4),
        "interactions_this_round": len(actions),
        "total_interactions": cumulative_interactions,
        "avg_response_ms": round(avg_response_ms, 2),
        "total_events": cumulative_events,
    }

    raw = [
        distribution.get("support", 0.0),
        distribution.get("oppose", 0.0),
        distribution.get("undecided", 0.0),
    ]
    rounded = [int(round(x * 100)) for x in raw]
    diff = 100 - sum(rounded)
    if diff != 0:
        max_idx = rounded.index(max(rounded))
        rounded[max_idx] += diff
    support_pct, oppose_pct, undecided_pct = rounded
    outcomes = [
        {"label": "Support",   "pct": support_pct,   "color": _OUTCOME_PALETTE["Support"]},
        {"label": "Oppose",    "pct": oppose_pct,    "color": _OUTCOME_PALETTE["Oppose"]},
        {"label": "Undecided", "pct": undecided_pct, "color": _OUTCOME_PALETTE["Undecided"]},
    ]

    events: list[dict] = []  # Phase 2: derive significant persuasion events here.

    # archetype_colors kept for callers that want to embed legend metadata,
    # but the frontend currently maps archetype -> color in the page.
    _ = archetype_colors

    return {
        "type": "round_log",
        "payload": {
            "simulation_id": simulation_id,
            "round": round_num,
            "total_rounds": total_rounds,
            "agents": agents_payload,
            "communities": communities,
            "edges": edges,
            "events": events,
            "metrics": metrics,
            "outcomes": outcomes,
        },
        "cohesion": cohesion,
        "entropy": entropy,
    }
