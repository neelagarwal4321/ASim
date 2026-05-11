"""
Report assembler: bundles outputs from the rest of the pipeline (aggregator,
narrative_synthesizer, counterfactual_prober, orchestrator influence rankings)
into one JSON-serializable dict ready for storage / API response.

Pure aggregation. No LLM calls, no DB writes.
"""

from __future__ import annotations

from agents.models import AgentProfile, AgentState


def _top_agent_view(item: dict) -> dict:
    agent: AgentProfile = item["agent"]
    state: AgentState = item["state"]
    return {
        "id": agent.id,
        "name": agent.name,
        "archetype": agent.archetype,
        "final_stance": round(state.stance, 3),
        "influence_score": round(state.influence_score, 3),
        "interaction_count": state.interaction_count,
        "moral_alignment": agent.moral_alignment,
        "appeal_type": agent.appeal_type,
    }


def assemble(
    scenario: str,
    verdict: dict,
    narrative: str,
    counterfactuals: list[dict],
    top_agents: list[dict],
    round_count: int,
    agent_count: int,
    hallucination: dict | None = None,
) -> dict:
    return {
        "scenario": scenario,
        "verdict": verdict["verdict"],
        "confidence": verdict["confidence"],
        "distribution": verdict["distribution"],
        "avg_stance": verdict.get("avg_stance"),
        "narrative": narrative,
        "counterfactuals": counterfactuals,
        "top_agents": [_top_agent_view(t) for t in top_agents],
        "round_count": round_count,
        "agent_count": agent_count,
        "hallucination": hallucination or {"level": "green", "total_warnings": 0,
                                           "total_actions": 0, "warning_rate": 0.0,
                                           "per_round": [], "details": []},
    }
