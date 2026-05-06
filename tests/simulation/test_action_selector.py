import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import random
from simulation.action_selector import select_action
from agents.generator import generate_agents


def test_returns_valid_action_type():
    agents = generate_agents(count=5, seed=1)
    agent = agents[0]
    from agents.models import AgentState
    state = AgentState(agent_id=agent.id)
    all_ids = [a.id for a in agents]
    rng = random.Random(42)

    action, target = select_action(agent, state, all_ids, rng)
    valid_actions = {"debate", "persuade", "broadcast", "challenge", "agree", "withdraw", "rally"}
    assert action in valid_actions


def test_targeted_actions_have_target():
    agents = generate_agents(count=5, seed=1)
    from agents.models import AgentState
    state = AgentState(agent_id=agents[0].id)
    all_ids = [a.id for a in agents]

    targeted_seen = False
    for seed in range(50):
        rng = random.Random(seed)
        action, target = select_action(agents[0], state, all_ids, rng)
        if action in {"debate", "persuade", "challenge"}:
            assert target is not None
            assert target != agents[0].id
            targeted_seen = True
            break
    assert targeted_seen, "Expected at least one targeted action in 50 trials"


def test_broadcast_and_rally_have_no_target():
    agents = generate_agents(count=5, seed=1)
    from agents.models import AgentState
    state = AgentState(agent_id=agents[0].id)
    all_ids = [a.id for a in agents]

    for seed in range(200):
        rng = random.Random(seed)
        action, target = select_action(agents[0], state, all_ids, rng)
        if action in {"broadcast", "rally", "agree", "withdraw"}:
            assert target is None
            break
