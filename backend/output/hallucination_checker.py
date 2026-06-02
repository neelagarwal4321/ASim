"""
Hallucination checker: scans completed round_logs for signs that an agent's
output drifted from physically plausible behavior. Pure Python, no LLM calls.

Three deterministic heuristics:

  - whiplash:       stance moved more than WHIPLASH_DELTA in a single round.
                    The persuasion engine caps deltas at 0.15 per round, so a
                    larger jump means the LLM ignored its prior state.
  - empty_response: agent free_text came back empty or whitespace-only despite
                    the parser accepting the round. Usually a sign the LLM
                    bailed mid-generation.
  - invalid_target: action.target_id points at an agent that does not exist in
                    the simulation. Indicates the LLM invented an addressee.

The output is rolled up into one of three levels — green / yellow / red —
based on the warning rate (warnings / total actions). Levels feed the Report
page banner so the user knows how much to trust deep-round reasoning.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulation.orchestrator import RoundResult

WHIPLASH_DELTA = 0.14       # just below per-round hard cap of 0.15
DETAILS_LIMIT = 20

LEVEL_GREEN_MAX = 0.05
LEVEL_YELLOW_MAX = 0.15


def _level_for_rate(rate: float) -> str:
    if rate <= LEVEL_GREEN_MAX:
        return "green"
    if rate <= LEVEL_YELLOW_MAX:
        return "yellow"
    return "red"


def check_hallucinations(
    round_logs: list["RoundResult"],
    valid_agent_ids: set[str],
) -> dict:
    """Roll up hallucination signals across all rounds.

    Args:
        round_logs:        Per-round results from the orchestrator.
        valid_agent_ids:   Set of every agent_id in the simulation. Used to
                           detect invented targets.

    Returns:
        Dict with `level`, `total_warnings`, `total_actions`, `warning_rate`,
        per-round breakdown, and a capped list of individual warnings.
    """
    prior_stance: dict[str, float] = {}
    total_actions = 0
    per_round: list[dict] = []
    details: list[dict] = []
    total_warnings = 0

    for rl in round_logs:
        whiplash = empty = invalid = 0
        for a in rl.actions:
            total_actions += 1

            previous = prior_stance.get(a.agent_id)
            if previous is not None and abs(a.stance - previous) > WHIPLASH_DELTA:
                whiplash += 1
                if len(details) < DETAILS_LIMIT:
                    details.append({
                        "round": rl.round_num,
                        "agent_id": a.agent_id,
                        "type": "whiplash",
                        "info": f"stance {previous:.2f} -> {a.stance:.2f}",
                    })

            if not a.free_text or not a.free_text.strip():
                empty += 1
                if len(details) < DETAILS_LIMIT:
                    details.append({
                        "round": rl.round_num,
                        "agent_id": a.agent_id,
                        "type": "empty_response",
                        "info": "free_text was empty",
                    })

            if a.target_id is not None and a.target_id not in valid_agent_ids:
                invalid += 1
                if len(details) < DETAILS_LIMIT:
                    details.append({
                        "round": rl.round_num,
                        "agent_id": a.agent_id,
                        "type": "invalid_target",
                        "info": f"target_id {a.target_id!r} not in simulation",
                    })

            prior_stance[a.agent_id] = a.stance

        round_warnings = whiplash + empty + invalid
        total_warnings += round_warnings
        per_round.append({
            "round": rl.round_num,
            "whiplash": whiplash,
            "empty": empty,
            "invalid_target": invalid,
        })

    rate = total_warnings / total_actions if total_actions else 0.0
    return {
        "level": _level_for_rate(rate),
        "total_warnings": total_warnings,
        "total_actions": total_actions,
        "warning_rate": round(rate, 4),
        "per_round": per_round,
        "details": details,
    }
