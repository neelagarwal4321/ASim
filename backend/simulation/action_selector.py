import random
from agents.models import AgentProfile, AgentState, ActionType

_ACTION_WEIGHT_FNS: dict[str, object] = {
    "debate":    lambda t: t.openness * 0.3 + t.extraversion * 0.3,
    "persuade":  lambda t: t.extraversion * 0.4 + (1 - t.agreeableness) * 0.2,
    "broadcast": lambda t: t.extraversion * 0.5 + t.conscientiousness * 0.2,
    "challenge": lambda t: (1 - t.agreeableness) * 0.4 + t.openness * 0.2,
    "agree":     lambda t: t.agreeableness * 0.5 + (1 - t.neuroticism) * 0.2,
    "withdraw":  lambda t: t.neuroticism * 0.3 + (1 - t.extraversion) * 0.3,
    "rally":     lambda t: t.extraversion * 0.3 + t.conscientiousness * 0.3,
}

_TARGETED_ACTIONS = frozenset({"debate", "persuade", "challenge"})


def select_action(
    agent: AgentProfile,
    state: AgentState,
    all_agent_ids: list[str],
    rng: random.Random,
) -> tuple[ActionType, str | None]:
    """Returns (action_type, target_agent_id | None)."""
    traits = agent.trait_vector
    actions = list(_ACTION_WEIGHT_FNS.keys())
    weights = [max(0.01, fn(traits)) for fn in _ACTION_WEIGHT_FNS.values()]

    action: ActionType = rng.choices(actions, weights=weights, k=1)[0]

    if action in _TARGETED_ACTIONS:
        candidates = [aid for aid in all_agent_ids if aid != agent.id]
        target = rng.choice(candidates) if candidates else None
    else:
        target = None

    return action, target
