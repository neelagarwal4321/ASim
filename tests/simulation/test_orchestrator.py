import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import contextlib
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from simulation.orchestrator import run_simulation, _apply_persuasion, SimulationResult
from simulation.state_manager import StateManager
from agents.generator import generate_agents


VALID_LLM_RESPONSE = (
    'The policy raises complex questions about freedom and public health.\n\n'
    '```json\n{"stance": 0.7, "emotion": "determined", "confidence": 0.8}\n```'
)


@contextlib.asynccontextmanager
async def _patched_sim(scenario="Test scenario", agent_count=5, rounds=2, seed=42,
                       llm_response=VALID_LLM_RESPONSE, narrative="Society debated the issue."):
    with patch("simulation.orchestrator.llm_executor") as mock_orch, \
         patch("output.narrative_synthesizer.llm_executor") as mock_narr:
        mock_orch.complete = AsyncMock(return_value=llm_response)
        mock_narr.complete = AsyncMock(return_value=narrative)
        result = await run_simulation(scenario, agent_count=agent_count,
                                      rounds=rounds, seed=seed)
        yield result


async def test_run_simulation_returns_simulation_result():
    async with _patched_sim() as result:
        assert isinstance(result, SimulationResult)


async def test_run_simulation_verdict_is_valid_string():
    async with _patched_sim() as result:
        valid_verdicts = (
            "Society reaches broad consensus in support",
            "Society rejects the proposition",
            "Society remains deeply divided",
            "Marginal support with significant opposition",
            "Marginal opposition with contested public opinion",
        )
        assert result.verdict in valid_verdicts


async def test_run_simulation_confidence_in_bounds():
    async with _patched_sim() as result:
        assert 0.0 <= result.confidence <= 1.0


async def test_run_simulation_distribution_sums_to_one():
    async with _patched_sim() as result:
        d = result.distribution
        total = d["support"] + d["oppose"] + d["undecided"]
        assert abs(total - 1.0) < 0.01


async def test_run_simulation_top_agents_nonempty():
    async with _patched_sim(agent_count=5) as result:
        assert len(result.top_agents) >= 1
        assert len(result.top_agents) <= 3


async def test_run_simulation_narrative_returned():
    async with _patched_sim(narrative="The debate concluded decisively.") as result:
        assert result.narrative == "The debate concluded decisively."


async def test_run_simulation_seed_produces_same_verdict():
    results = []
    for _ in range(2):
        with patch("simulation.orchestrator.llm_executor") as m_orch, \
             patch("output.narrative_synthesizer.llm_executor") as m_narr:
            m_orch.complete = AsyncMock(return_value=VALID_LLM_RESPONSE)
            m_narr.complete = AsyncMock(return_value="Narrative.")
            r = await run_simulation("Same scenario", agent_count=5, rounds=1, seed=99)
            results.append(r)
    assert results[0].verdict == results[1].verdict


async def test_run_simulation_llm_failure_does_not_crash():
    call_count = 0

    async def flaky_complete(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count % 3 == 0:
            raise ConnectionError("Ollama timeout")
        return VALID_LLM_RESPONSE

    with patch("simulation.orchestrator.llm_executor") as m_orch, \
         patch("output.narrative_synthesizer.llm_executor") as m_narr:
        m_orch.complete = flaky_complete
        m_narr.complete = AsyncMock(return_value="Narrative despite failures.")
        result = await run_simulation("Resilience test", agent_count=6, rounds=1, seed=7)

    assert result is not None
    assert result.verdict is not None


async def test_run_simulation_missing_json_triggers_retry():
    responses = iter([
        "I have thoughts on this.",
        VALID_LLM_RESPONSE,
    ] * 50)

    async def side_effect(**kwargs):
        return next(responses)

    with patch("simulation.orchestrator.llm_executor") as m_orch, \
         patch("output.narrative_synthesizer.llm_executor") as m_narr:
        m_orch.complete = side_effect
        m_narr.complete = AsyncMock(return_value="Narrative.")
        result = await run_simulation("Retry test", agent_count=3, rounds=1, seed=1)

    assert result is not None


def test_apply_persuasion_updates_target_stance():
    from agents.models import RoundAction

    agents = generate_agents(count=3, seed=10)
    agent_map = {a.id: a for a in agents}
    state_mgr = StateManager()
    for a in agents:
        state_mgr.init_agent_state(a.id)

    actor, target = agents[0], agents[1]
    actor_state = state_mgr.get_state(actor.id)
    actor_state.stance = 1.0
    actor_state.confidence = 1.0
    state_mgr.update_state(actor_state)

    target_tv = target.trait_vector.model_copy(
        update={"moral_rigidity": 0.0, "susceptibility": 1.0}
    )
    agents[1] = target.model_copy(update={"trait_vector": target_tv})
    agent_map = {a.id: a for a in agents}

    target_state = state_mgr.get_state(target.id)
    target_state.stance = 0.0
    state_mgr.update_state(target_state)

    action = RoundAction(
        agent_id=actor.id, name=actor.name, archetype=actor.archetype,
        action="persuade", target_id=target.id,
        free_text="You must agree!", stance=1.0, emotion="passionate", confidence=1.0,
    )
    state_mgr.update_trust(actor.id, target.id, 0.9)

    _apply_persuasion([action], agent_map, state_mgr)

    updated = state_mgr.get_state(target.id)
    assert updated.stance > 0.0
