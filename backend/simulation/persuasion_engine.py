from agents.models import AgentProfile, AgentState, RoundAction

_APPEAL_EMOTION_MATCH: dict[str, frozenset] = {
    "emotional":  frozenset({"angry", "fearful", "passionate", "hopeful"}),
    "rational":   frozenset({"determined", "neutral"}),
    "social":     frozenset({"optimistic", "hopeful"}),
    "authority":  frozenset({"neutral", "determined"}),
}


def resolve_persuasion(
    actor: AgentProfile,
    actor_state: AgentState,
    actor_action: RoundAction,
    target: AgentProfile,
    target_state: AgentState,
    trust_score: float,
    social_proof: float,
    repetition_bonus: float,
) -> float:
    """Compute stance delta to apply to target. Returns 0.0 if persuasion threshold not met."""
    matched = _APPEAL_EMOTION_MATCH.get(actor.appeal_type, frozenset())
    emotional_resonance = 1.0 if target_state.emotion in matched else 0.0

    persuasion_score = (
        trust_score                      * 0.30
        + actor_action.confidence        * 0.25
        + emotional_resonance            * 0.20
        + social_proof                   * 0.15
        + min(0.30, repetition_bonus)    * 0.10
    )

    susceptibility_threshold = (1.0 - target.trait_vector.susceptibility) * target_state.confidence
    if persuasion_score <= susceptibility_threshold:
        return 0.0

    direction = 1.0 if actor_state.stance > target_state.stance else -1.0
    delta = persuasion_score * (1.0 - target.trait_vector.moral_rigidity) * 0.2 * direction

    # Hard cap: ±0.15 per round
    delta = max(-0.15, min(0.15, delta))

    # Moral rigidity ≥ 0.9 → hard cap at ±0.02
    if target.trait_vector.moral_rigidity >= 0.9:
        delta = max(-0.02, min(0.02, delta))

    return delta
