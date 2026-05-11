"""
Build RoundLogEdge[] from the simulation's trust dict.

Emits only "significant" trust pairs to keep the WS payload bounded:
  - positive: trust >= POSITIVE_THRESHOLD
  - hostile:  trust <= HOSTILE_THRESHOLD
  - covert:   trust between, source is Manipulator archetype

Pairs near 0.5 (neutral) are skipped. Hard cap MAX_EDGES per round so a 500-
agent sim does not flood the frontend with 250k entries.
"""

from __future__ import annotations

from agents.models import AgentProfile

POSITIVE_THRESHOLD = 0.62
HOSTILE_THRESHOLD = 0.38
COVERT_ARCHETYPE = "Manipulator"
MAX_EDGES = 200


def _edge_type(trust: float, source_archetype: str) -> str | None:
    if source_archetype == COVERT_ARCHETYPE and HOSTILE_THRESHOLD < trust < POSITIVE_THRESHOLD:
        return "covert"
    if trust >= POSITIVE_THRESHOLD:
        return "positive"
    if trust <= HOSTILE_THRESHOLD:
        return "hostile"
    return None


def build_edges(
    agents: list[AgentProfile],
    trust: dict[tuple[str, str], float],
) -> list[dict]:
    by_id = {a.id: a for a in agents}
    candidates: list[tuple[float, dict]] = []
    for (src, dst), weight in trust.items():
        if src not in by_id or dst not in by_id:
            continue
        kind = _edge_type(weight, by_id[src].archetype)
        if kind is None:
            continue
        # Strength: distance from neutral, normalized to [0, 1].
        strength = round(abs(weight - 0.5) * 2, 3)
        # Sort key: prioritize most extreme (strongest) edges within MAX_EDGES.
        candidates.append((abs(weight - 0.5), {
            "source": src,
            "target": dst,
            "type": kind,
            "strength": strength,
        }))

    candidates.sort(key=lambda c: c[0], reverse=True)
    return [edge for _, edge in candidates[:MAX_EDGES]]
