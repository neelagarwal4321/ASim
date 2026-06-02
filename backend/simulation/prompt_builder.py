import json

from agents.models import AgentProfile, AgentState, ActionType


def build_prompt(
    agent: AgentProfile,
    state: AgentState,
    action: ActionType,
    target_name: str | None,
    scenario: str,
    round_num: int,
    trust_scores: dict[str, float],
    total_rounds: int,
) -> tuple[str, str, str]:
    """Assemble the 6-block prompt.

    Returns (static_system, dynamic_context, user_message).
    static_system = Blocks 1-3 (identity, behavioral, moral) — cached in Anthropic.
    dynamic_context = Blocks 4-5 (social context, memory) — rebuilt every round.
    user_message = Block 6 (action instruction + JSON spec).
    """
    t = agent.trait_vector

    # Block 1: Identity
    block1 = (
        f"You are {agent.name}, a {agent.archetype}.\n\n"
        f"Your core beliefs:\n"
        + "\n".join(f"- {b}" for b in agent.core_beliefs)
        + f"\n\nYour voice: {agent.voice_style}"
    )

    # Block 2: Behavioral instructions
    block2 = (
        f"Your behavioral profile:\n"
        f"- Openness to new ideas: {t.openness:.2f}/1.0\n"
        f"- Conscientiousness: {t.conscientiousness:.2f}/1.0\n"
        f"- Extraversion: {t.extraversion:.2f}/1.0\n"
        f"- Agreeableness: {t.agreeableness:.2f}/1.0\n"
        f"- Emotional reactivity: {t.neuroticism:.2f}/1.0\n\n"
        f"You tend to make {agent.appeal_type} arguments.\n"
        f"You stay consistent with your identity even under social pressure."
    )

    # Block 3: Moral framing
    rigidity_note = (
        "You are highly resistant to changing your fundamental values."
        if t.moral_rigidity > 0.7
        else "You can update your positions when presented with compelling arguments."
    )
    block3 = (
        f"Your moral framework: {agent.moral_alignment}.\n"
        f"Moral rigidity: {t.moral_rigidity:.2f}/1.0\n"
        f"{rigidity_note}"
    )

    static_system = f"{block1}\n\n{block2}\n\n{block3}"

    # Block 4: Social context
    if trust_scores:
        trust_lines = "\n".join(
            f"- {name}: trust {score:.2f}"
            for name, score in sorted(trust_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        )
        relationship_text = trust_lines
    else:
        relationship_text = "No established relationships yet."

    block4 = (
        f"Current scenario: {scenario}\n\n"
        f"Round {round_num} of {total_rounds}.\n\n"
        f"Your current relationships:\n{relationship_text}"
    )

    # Block 5: Memory
    memory_note = (
        f"What you remember: {state.memory_text}"
        if state.memory_text
        else "This is the first round — form your initial position based on your beliefs."
    )
    block5 = (
        f"Your current state:\n"
        f"- Stance on the issue: {state.stance:.2f} (0.0 = strongly oppose, 1.0 = strongly support)\n"
        f"- Current emotion: {state.emotion}\n"
        f"- Confidence: {state.confidence:.2f}\n\n"
        f"{memory_note}"
    )

    dynamic_context = f"{block4}\n\n{block5}"

    # Block 6: Action instruction + JSON spec
    target_str = f" directed at {target_name}" if target_name else ""
    target_id_val = json.dumps(target_name) if target_name else "null"
    block6 = (
        f"Your action this round: {action}{target_str}.\n\n"
        f"Respond in character as {agent.name}. Stay true to your voice and beliefs.\n\n"
        f"End your response with this exact JSON block:\n"
        f'{{\n'
        f'  "action": "{action}",\n'
        f'  "target_id": {target_id_val},\n'
        f'  "stance": <your current stance 0.0-1.0>,\n'
        f'  "emotion": "<neutral|optimistic|angry|fearful|determined|hopeful|cynical|passionate>",\n'
        f'  "confidence": <0.0-1.0>,\n'
        f'  "argument_quality": <0.0-1.0>\n'
        f'}}'
    )

    return static_system, dynamic_context, block6
