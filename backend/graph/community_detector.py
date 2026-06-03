"""
Community detection over the simulation's agent population.

Two-stage algorithm, both pure Python:

  1. Seed buckets by stance proximity. Stance is the strongest visible signal
     of belief alignment, and bucketing is O(N).
  2. Refine by trust: for each bucket, run a BFS over the high-trust subgraph
     and split any bucket whose members are not all connected through trust
     edges. This catches the case where two agents land in the same stance
     bucket but never interact, so they should not share a community.

Result is a list of community dicts ready for the WS round_log payload.

Deferred for later phases: Louvain / Leiden weighted modularity, archetype
similarity weighting, edge-betweenness. The current shape ships enough signal
for the LiveSimulation Communities panel without a NetworkX dependency.
"""

from __future__ import annotations

from collections import deque

from agents.models import AgentProfile, AgentState

# Stance buckets (lower bound inclusive, upper bound exclusive — last is closed).
_BUCKETS = [
    (0.00, 0.20, "Strong Oppose",  "#FF3B6F"),
    (0.20, 0.40, "Lean Oppose",    "#FF6B9D"),
    (0.40, 0.60, "Undecided",      "#8A9BBE"),
    (0.60, 0.80, "Lean Support",   "#00D4C8"),
    (0.80, 1.01, "Strong Support", "#00C96B"),
]

TRUST_EDGE_THRESHOLD = 0.55
MIN_COMMUNITY_SIZE = 2


def _bucket_for(stance: float) -> tuple[str, str]:
    for lo, hi, name, color in _BUCKETS:
        if lo <= stance < hi:
            return name, color
    return _BUCKETS[-1][2], _BUCKETS[-1][3]


def _bfs_components(
    members: list[str],
    trust: dict[tuple[str, str], float],
) -> list[list[str]]:
    """Split members into connected components on the high-trust subgraph.

    A single member with no qualifying edges still counts as a component of
    size 1 — the caller filters by MIN_COMMUNITY_SIZE.
    """
    member_set = set(members)
    adj: dict[str, set[str]] = {m: set() for m in members}
    for (a, b), w in trust.items():
        if w < TRUST_EDGE_THRESHOLD:
            continue
        if a in member_set and b in member_set:
            adj[a].add(b)
            adj[b].add(a)

    seen: set[str] = set()
    components: list[list[str]] = []
    for m in members:
        if m in seen:
            continue
        component: list[str] = []
        q = deque([m])
        seen.add(m)
        while q:
            node = q.popleft()
            component.append(node)
            for neighbour in adj[node]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    q.append(neighbour)
        components.append(component)
    return components


def detect_communities(
    agents: list[AgentProfile],
    states: list[AgentState],
    trust: dict[tuple[str, str], float],
) -> list[dict]:
    """Return communities shaped as RoundLogCommunity (id/name/color/member_ids).

    Stance bucketing first, BFS refinement second. A bucket with no trust
    edges among its members still yields one community per member — single-
    member groups are dropped to keep the panel readable.
    """
    state_by_id = {s.agent_id: s for s in states}
    buckets: dict[str, dict] = {}
    for a in agents:
        state = state_by_id.get(a.id)
        if state is None:
            continue
        name, color = _bucket_for(state.stance)
        bucket = buckets.setdefault(name, {"name": name, "color": color, "members": []})
        bucket["members"].append(a.id)

    communities: list[dict] = []
    for bucket in buckets.values():
        components = _bfs_components(bucket["members"], trust)
        # If trust hasn't formed yet, every component is size 1 and we'd
        # drop everything. Fall back to the bucket itself as one community.
        if all(len(c) == 1 for c in components):
            components = [bucket["members"]]
        eligible = [c for c in components if len(c) >= MIN_COMMUNITY_SIZE]
        for idx, comp in enumerate(eligible):
            # Stable ID: slug of bucket name + sub-index so the frontend can
            # track the same community across rounds.
            slug = bucket["name"].lower().replace(" ", "-")
            communities.append({
                "id": f"{slug}-{idx}",
                "name": bucket["name"],
                "color": bucket["color"],
                "member_ids": comp,
            })
    return communities
