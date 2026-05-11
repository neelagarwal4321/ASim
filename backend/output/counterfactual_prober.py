"""
Counterfactual prober: applies cheap, deterministic perturbations to the final
state and recomputes the verdict so we can show users plausible "what if" arcs
without re-running the full LLM simulation.

Each probe is a pure function: (states, agents) -> altered_states. We feed the
altered states back through aggregator.compute_verdict and report the delta.

Probes intentionally avoid the LLM. The report's narrative already burns one
LLM call; counterfactuals are cheap analytical commentary on top of it.
"""

from __future__ import annotations

from copy import deepcopy

from agents.models import AgentProfile, AgentState
from output.aggregator import compute_verdict


def _without_archetype(
    states: list[AgentState],
    agents: list[AgentProfile],
    archetype: str,
) -> list[AgentState]:
    excluded = {a.id for a in agents if a.archetype == archetype}
    return [s for s in states if s.agent_id not in excluded]


def _collapse_toward_mean(states: list[AgentState], pull: float) -> list[AgentState]:
    if not states:
        return states
    mean = sum(s.stance for s in states) / len(states)
    out = []
    for s in states:
        copy = deepcopy(s)
        copy.stance = max(0.0, min(1.0, s.stance + (mean - s.stance) * pull))
        out.append(copy)
    return out


def _amplify_polarization(states: list[AgentState], strength: float) -> list[AgentState]:
    out = []
    for s in states:
        copy = deepcopy(s)
        delta = (s.stance - 0.5) * strength
        copy.stance = max(0.0, min(1.0, s.stance + delta))
        out.append(copy)
    return out


def _delta_label(delta: float) -> str:
    if abs(delta) < 0.02:
        return "negligible"
    if abs(delta) < 0.08:
        return "minor"
    if abs(delta) < 0.15:
        return "moderate"
    return "large"


def run_probes(
    final_states: list[AgentState],
    agents: list[AgentProfile],
    baseline_verdict: dict,
) -> list[dict]:
    """
    Run a fixed set of heuristic probes against the final state.

    Returns one entry per probe with the altered verdict alongside the delta
    versus the baseline. Empty result is a valid response if no probe applies
    (e.g. zero agents).
    """
    if not final_states or not agents:
        return []

    probes: list[dict] = []
    baseline_avg = baseline_verdict.get("avg_stance", 0.5)

    has_manipulators = any(a.archetype == "Manipulator" for a in agents)
    if has_manipulators:
        altered = _without_archetype(final_states, agents, "Manipulator")
        if altered:
            v = compute_verdict(altered)
            probes.append({
                "lever": "no_manipulators",
                "description": "Society without Manipulator archetypes",
                "verdict": v["verdict"],
                "confidence": v["confidence"],
                "distribution": v["distribution"],
                "avg_stance_delta": round(v["avg_stance"] - baseline_avg, 3),
                "magnitude": _delta_label(v["avg_stance"] - baseline_avg),
                "explanation": (
                    "Removed Manipulator agents and recomputed the verdict from the "
                    "remaining population. Highlights how much of the outcome was "
                    "driven by bad-faith persuasion versus genuine consensus."
                ),
            })

    cohesive = _collapse_toward_mean(final_states, pull=0.6)
    v = compute_verdict(cohesive)
    probes.append({
        "lever": "low_rigidity_population",
        "description": "Population with lower moral rigidity (60% pull toward mean)",
        "verdict": v["verdict"],
        "confidence": v["confidence"],
        "distribution": v["distribution"],
        "avg_stance_delta": round(v["avg_stance"] - baseline_avg, 3),
        "magnitude": _delta_label(v["avg_stance"] - baseline_avg),
        "explanation": (
            "Pulled every agent 60% of the way to the population mean to simulate a "
            "less rigid society. Larger consensus shifts indicate the outcome was "
            "held in place by moral rigidity rather than reasoned agreement."
        ),
    })

    polarized = _amplify_polarization(final_states, strength=0.5)
    v = compute_verdict(polarized)
    probes.append({
        "lever": "amplified_polarization",
        "description": "Stances pushed 50% further from center",
        "verdict": v["verdict"],
        "confidence": v["confidence"],
        "distribution": v["distribution"],
        "avg_stance_delta": round(v["avg_stance"] - baseline_avg, 3),
        "magnitude": _delta_label(v["avg_stance"] - baseline_avg),
        "explanation": (
            "Pushed every stance 50% further from the neutral midpoint. Models a "
            "media environment that hardens existing positions and exposes how "
            "fragile the actual consensus was."
        ),
    })

    return probes
