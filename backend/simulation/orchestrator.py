import asyncio
import logging
import random
from dataclasses import dataclass

from agents.models import AgentProfile, AgentState, RoundAction
from agents.generator import generate_agents
from graph.community_detector import detect_communities
from llm.executor import llm_executor
from llm.response_parser import parse_response
from memory.compressor import update_memory
from output.aggregator import compute_verdict
from output.counterfactual_prober import run_probes
from output.hallucination_checker import check_hallucinations
from output.narrative_synthesizer import generate_narrative
from output.report_assembler import assemble as assemble_report
from services.redis_publisher import publish_round
from simulation.action_selector import select_action
from simulation.persuasion_engine import resolve_persuasion
from simulation.prompt_builder import build_prompt
from simulation.round_log_builder import build_round_log
from simulation.state_manager import StateManager

logger = logging.getLogger(__name__)


@dataclass
class RoundResult:
    round_num: int
    actions: list[RoundAction]
    stance_distribution: dict


@dataclass
class SimulationResult:
    verdict: str
    confidence: float
    distribution: dict
    top_agents: list[dict]
    narrative: str
    counterfactuals: list[dict]
    hallucination: dict
    report: dict


async def run_simulation(
    scenario: str,
    agent_count: int = 50,
    rounds: int = 5,
    seed: int | None = None,
    api_key: str | None = None,
    simulation_id: str | None = None,
) -> SimulationResult:
    rng = random.Random(seed)
    agents = generate_agents(count=agent_count, seed=seed)
    agent_map: dict[str, AgentProfile] = {a.id: a for a in agents}

    state_mgr = StateManager()
    for agent in agents:
        state = state_mgr.init_agent_state(agent.id)
        # Initial stance varies by openness — skeptics start lower, open minds higher
        base = 0.30 + agent.trait_vector.openness * 0.40
        state.stance = max(0.0, min(1.0, base + rng.gauss(0, 0.12)))
        state_mgr.update_state(state)

    round_logs: list[RoundResult] = []
    cumulative_interactions = 0
    cumulative_events = 0
    prev_cohesion: float | None = None
    prev_entropy: float | None = None

    for round_num in range(1, rounds + 1):
        logger.info("Round %d/%d", round_num, rounds)
        actions = await _run_round(
            scenario=scenario,
            agents=agents,
            agent_map=agent_map,
            state_mgr=state_mgr,
            round_num=round_num,
            total_rounds=rounds,
            rng=rng,
            api_key=api_key,
            prior_distribution=round_logs[-1].stance_distribution if round_logs else None,
        )

        all_states = state_mgr.get_all_states()
        n = len(all_states)
        support = sum(1 for s in all_states if s.stance >= 0.6) / n
        oppose = sum(1 for s in all_states if s.stance <= 0.4) / n
        undecided = 1.0 - support - oppose

        dist = {"support": round(support, 3), "oppose": round(oppose, 3), "undecided": round(undecided, 3)}
        round_logs.append(RoundResult(round_num=round_num, actions=actions, stance_distribution=dist))
        cumulative_interactions += len(actions)
        logger.info("  Support %.0f%%  Oppose %.0f%%  Undecided %.0f%%", support * 100, oppose * 100, undecided * 100)

        if simulation_id:
            try:
                envelope = build_round_log(
                    simulation_id=simulation_id,
                    round_num=round_num,
                    total_rounds=rounds,
                    actions=actions,
                    states=all_states,
                    agents=agents,
                    archetype_colors={},
                    distribution=dist,
                    cumulative_interactions=cumulative_interactions,
                    cumulative_events=cumulative_events,
                    prev_cohesion=prev_cohesion,
                    prev_entropy=prev_entropy,
                    trust=state_mgr.get_all_trust(),
                )
                publish_round(simulation_id, {"type": envelope["type"], "payload": envelope["payload"]})
                prev_cohesion = envelope["cohesion"]
                prev_entropy = envelope["entropy"]
            except Exception as exc:
                logger.warning("Redis publish round %d failed: %s", round_num, exc)

    final_states = state_mgr.get_all_states()
    verdict_data = compute_verdict(final_states)
    narrative = await generate_narrative(
        scenario=scenario,
        round_logs=round_logs,
        verdict=verdict_data,
        api_key=api_key,
    )

    sorted_states = sorted(final_states, key=lambda s: s.influence_score, reverse=True)
    top_agents = [
        {"agent": agent_map[s.agent_id], "state": s}
        for s in sorted_states[:3]
        if s.agent_id in agent_map
    ]

    counterfactuals = run_probes(final_states, agents, verdict_data)
    hallucination = check_hallucinations(round_logs, {a.id for a in agents})
    report = assemble_report(
        scenario=scenario,
        verdict=verdict_data,
        narrative=narrative,
        counterfactuals=counterfactuals,
        top_agents=top_agents,
        round_count=len(round_logs),
        agent_count=len(final_states),
        hallucination=hallucination,
    )

    result = SimulationResult(
        verdict=verdict_data["verdict"],
        confidence=verdict_data["confidence"],
        distribution=verdict_data["distribution"],
        top_agents=top_agents,
        narrative=narrative,
        counterfactuals=counterfactuals,
        hallucination=hallucination,
        report=report,
    )

    final_communities = detect_communities(agents, final_states, state_mgr.get_all_trust())

    if simulation_id:
        try:
            publish_round(simulation_id, {
                "type": "complete",
                "payload": {
                    "simulation_id": simulation_id,
                    "total_rounds": len(round_logs),
                    "agent_count": len(final_states),
                    "community_count": len(final_communities),
                },
                "verdict": verdict_data["verdict"],
                "confidence": verdict_data["confidence"],
                "distribution": verdict_data["distribution"],
                "narrative": narrative,
            })
        except Exception as exc:
            logger.warning("Redis publish complete failed: %s", exc)

    return result


async def _run_round(
    scenario: str,
    agents: list[AgentProfile],
    agent_map: dict[str, AgentProfile],
    state_mgr: StateManager,
    round_num: int,
    total_rounds: int,
    rng: random.Random,
    api_key: str | None,
    prior_distribution: dict | None = None,
) -> list[RoundAction]:
    all_ids = [a.id for a in agents]
    actions: list[RoundAction] = []

    for agent in agents:
        state = state_mgr.get_state(agent.id)
        action_type, target_id = select_action(agent, state, all_ids, rng)

        trust_context = {
            agent_map[oid].name: state_mgr.get_trust(agent.id, oid)
            for oid in all_ids
            if oid != agent.id
        }

        target_name = agent_map[target_id].name if target_id and target_id in agent_map else None
        static_sys, dynamic_ctx, user_msg = build_prompt(
            agent=agent, state=state, action=action_type, target_name=target_name,
            scenario=scenario, round_num=round_num,
            trust_scores=trust_context, total_rounds=total_rounds,
        )

        free_text, json_data = "", {}
        try:
            raw = await llm_executor.complete(
                user_message=user_msg,
                static_system=static_sys,
                dynamic_context=dynamic_ctx,
                api_key=api_key,
            )
            free_text, json_data = parse_response(raw)

            if not json_data:
                logger.warning("Agent %s round %d: retrying — no JSON", agent.id[:8], round_num)
                retry_msg = (
                    user_msg + "\n\nYour previous response was missing the required JSON block. "
                    "Respond again and end with the JSON block exactly as specified."
                )
                raw = await llm_executor.complete(
                    user_message=retry_msg, static_system=static_sys,
                    dynamic_context=dynamic_ctx, api_key=api_key,
                )
                free_text, json_data = parse_response(raw)

        except Exception as exc:
            logger.error("Agent %s round %d LLM error: %s", agent.id[:8], round_num, exc)
            continue

        if not json_data:
            logger.warning("Agent %s round %d: skipping after retry failure", agent.id[:8], round_num)
            continue

        state.stance = max(0.0, min(1.0, float(json_data.get("stance", state.stance))))
        state.emotion = json_data.get("emotion", state.emotion)
        state.confidence = max(0.0, min(1.0, float(json_data.get("confidence", state.confidence))))
        state.last_action = action_type
        state.last_target = target_id
        state.interaction_count += 1
        state_mgr.update_state(state)

        try:
            arg_q = float(json_data.get("argument_quality", 0.5))
        except (TypeError, ValueError):
            arg_q = 0.5
        arg_q = max(0.0, min(1.0, arg_q))

        round_action = RoundAction(
            agent_id=agent.id, name=agent.name, archetype=agent.archetype,
            action=action_type, target_id=target_id,
            free_text=free_text or f"[{agent.name} performs {action_type}]",
            stance=state.stance, emotion=state.emotion, confidence=state.confidence,
            argument_quality=arg_q,
        )
        actions.append(round_action)

        state.memory_text = update_memory(state, round_action, prior_distribution or {}, round_num)
        state_mgr.update_state(state)

    _apply_persuasion(actions, agent_map, state_mgr)
    return actions


def _apply_persuasion(
    actions: list[RoundAction],
    agent_map: dict[str, AgentProfile],
    state_mgr: StateManager,
) -> None:
    all_states = state_mgr.get_all_states()
    n = len(all_states)

    for action in actions:
        if not action.target_id or action.target_id not in agent_map:
            continue

        actor = agent_map[action.agent_id]
        actor_state = state_mgr.get_state(action.agent_id)
        target = agent_map[action.target_id]
        target_state = state_mgr.get_state(action.target_id)
        trust = state_mgr.get_trust(action.agent_id, action.target_id)

        # Social proof: fraction of agents sharing actor's stance direction
        same = sum(1 for s in all_states if (s.stance >= 0.5) == (actor_state.stance >= 0.5))
        social_proof = same / n if n > 0 else 0.5

        # Repetition bonus capped at 0.30
        repetition_bonus = min(0.30, state_mgr.get_trust(action.agent_id, action.target_id) * 0.3)

        delta = resolve_persuasion(
            actor=actor, actor_state=actor_state, actor_action=action,
            target=target, target_state=target_state,
            trust_score=trust, social_proof=social_proof, repetition_bonus=repetition_bonus,
        )

        if delta != 0.0:
            target_state.stance = max(0.0, min(1.0, target_state.stance + delta))
            state_mgr.update_state(target_state)
            actor_state.influence_score += abs(delta)
            state_mgr.update_state(actor_state)
            state_mgr.update_trust(action.agent_id, action.target_id, 0.02)
