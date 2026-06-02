"""
Memory compression for agents.

Per CLAUDE.md round order, each round writes a compact memory entry into
`state.memory_text`. The prompt builder reads it back into block 5 the next
round. Without compression the memory string grows unbounded; with it, prompts
stay flat across long simulations.

Format: pipe-separated entries joined by " || ". Oldest entries collapse into
a single "SUM(N)" tag once total entries exceed MAX_RECENT, so callers never
see the older raw entries again — just the count.

Deterministic, no LLM call. Memory budget per agent is O(MAX_RECENT) entries.
"""

from __future__ import annotations

from agents.models import AgentState, RoundAction

MAX_RECENT = 3
SEP = " || "


def _compose_entry(action: RoundAction, distribution: dict, round_num: int) -> str:
    parts = [f"R{round_num}", action.action]
    if action.target_id:
        parts.append(f"->{action.target_id[:8]}")
    parts.append(f"stance={action.stance:.2f}")
    parts.append(f"emo={action.emotion}")
    if distribution:
        dominant_label = max(distribution, key=distribution.get, default="undecided")
        dominant_value = distribution[dominant_label]
        parts.append(f"crowd={dominant_label}{int(dominant_value * 100)}%")
    return ":".join(parts)


def _existing_entries(memory_text: str | None) -> list[str]:
    if not memory_text:
        return []
    return [p for p in memory_text.split(SEP) if p]


def _compress(entries: list[str]) -> list[str]:
    """Collapse anything older than MAX_RECENT entries into a SUM(N) tag.

    A SUM(N) entry counts how many original rounds were merged. If the head of
    the list is already a SUM(N), increment N rather than nesting summaries.
    """
    if len(entries) <= MAX_RECENT:
        return entries

    older = entries[:-MAX_RECENT]
    recent = entries[-MAX_RECENT:]
    # Separate any existing SUM tag from plain entries so we don't double-count.
    # A SUM(N) entry already represents N collapsed rounds; plain entries each count as 1.
    sum_entry = next((e for e in older if e.startswith("SUM(")), None)
    existing_total = _decode_sum(sum_entry) if sum_entry else 0
    fresh_entries = [e for e in older if not e.startswith("SUM(")]
    extra = existing_total + sum(_decode_sum(e) for e in fresh_entries)
    summary = f"SUM({extra})"
    return [summary] + recent


def _decode_sum(entry: str) -> int:
    if entry.startswith("SUM(") and entry.endswith(")"):
        try:
            return int(entry[4:-1])
        except ValueError:
            return 1
    return 1


def update_memory(
    state: AgentState,
    action: RoundAction,
    distribution: dict,
    round_num: int,
) -> str:
    """Return the new memory_text after folding this round's action in."""
    entry = _compose_entry(action, distribution, round_num)
    entries = _existing_entries(state.memory_text)
    entries.append(entry)
    entries = _compress(entries)
    return SEP.join(entries)
