import logging
from llm.executor import llm_executor

logger = logging.getLogger(__name__)


async def generate_narrative(
    scenario: str,
    round_logs: list,
    verdict: dict,
    api_key: str | None = None,
) -> str:
    """Generate a 3-5 sentence narrative arc via a single LLM call."""
    round_summaries = "\n".join(
        f"Round {rl.round_num}: {rl.stance_distribution['support']:.0%} support, "
        f"{rl.stance_distribution['oppose']:.0%} oppose, "
        f"{rl.stance_distribution['undecided']:.0%} undecided"
        for rl in round_logs
    )

    system = (
        "You are a political analyst writing a concise narrative arc. "
        "Write exactly 3-5 sentences describing how society responded to the scenario. "
        "Focus on the emotional journey, key turning points, and why the outcome emerged. "
        "Write in past tense, journalistic style. Be specific and vivid. "
        "Do not include JSON or structured data — plain prose only."
    )

    prompt = (
        f"Scenario: {scenario}\n\n"
        f"Round progression:\n{round_summaries}\n\n"
        f"Final outcome: {verdict['verdict']} (confidence: {verdict['confidence']:.0%})\n"
        f"Distribution: {verdict['distribution']['support']:.0%} support, "
        f"{verdict['distribution']['oppose']:.0%} oppose\n\n"
        f"Write the narrative arc in 3-5 sentences."
    )

    try:
        narrative = await llm_executor.complete(
            user_message=prompt,
            static_system=system,
            api_key=api_key,
        )
        return narrative.strip()
    except Exception as exc:
        logger.error("Narrative generation failed: %s", exc)
        dist = verdict["distribution"]
        return (
            f"The scenario unfolded with divergent societal responses. "
            f"After {len(round_logs)} rounds of debate, {dist['support']:.0%} of agents expressed support "
            f"while {dist['oppose']:.0%} remained opposed. "
            f"The final outcome — {verdict['verdict'].lower()} — emerged from the complex interplay "
            f"of competing beliefs and social pressures."
        )
