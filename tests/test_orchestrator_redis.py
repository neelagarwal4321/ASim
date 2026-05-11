import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_publish_round_called_per_round_when_simulation_id_given():
    mock_response = 'Response. {"stance": 0.55, "emotion": "engaged", "confidence": 0.65}'
    with patch("simulation.orchestrator.publish_round") as mock_pub, \
         patch("simulation.orchestrator.llm_executor") as mock_llm:
        mock_llm.complete = AsyncMock(return_value=mock_response)
        from simulation.orchestrator import run_simulation
        await run_simulation(
            scenario="test scenario",
            agent_count=3,
            rounds=2,
            simulation_id="test-sim-001",
        )
    # 2 round events + 1 complete event = 3 calls
    assert mock_pub.call_count == 3
    types = [c.args[1]["type"] for c in mock_pub.call_args_list]
    assert types.count("round_log") == 2
    assert types.count("complete") == 1


@pytest.mark.asyncio
async def test_no_publish_without_simulation_id():
    mock_response = 'Test. {"stance": 0.5, "emotion": "neutral", "confidence": 0.5}'
    with patch("simulation.orchestrator.publish_round") as mock_pub, \
         patch("simulation.orchestrator.llm_executor") as mock_llm:
        mock_llm.complete = AsyncMock(return_value=mock_response)
        from simulation.orchestrator import run_simulation
        await run_simulation(scenario="test", agent_count=2, rounds=1)
    mock_pub.assert_not_called()


@pytest.mark.asyncio
async def test_round_payload_has_required_fields():
    mock_response = 'Response. {"stance": 0.6, "emotion": "hopeful", "confidence": 0.7}'
    with patch("simulation.orchestrator.publish_round") as mock_pub, \
         patch("simulation.orchestrator.llm_executor") as mock_llm:
        mock_llm.complete = AsyncMock(return_value=mock_response)
        from simulation.orchestrator import run_simulation
        await run_simulation(
            scenario="test",
            agent_count=2,
            rounds=1,
            simulation_id="test-sim-002",
        )
    round_call = next(c for c in mock_pub.call_args_list if c.args[1]["type"] == "round_log")
    payload = round_call.args[1]["payload"]
    assert payload["simulation_id"] == "test-sim-002"
    assert "round" in payload
    assert "total_rounds" in payload
    assert "agents" in payload
    assert "communities" in payload
    assert "edges" in payload
    assert "events" in payload
    assert "metrics" in payload
    assert "outcomes" in payload
    assert all(
        {"id", "name", "archetype", "stance", "emotion", "action", "message", "influence", "community_id"} <= set(a.keys())
        for a in payload["agents"]
    )
    assert {"cohesion", "entropy", "interactions_this_round", "total_interactions"} <= set(payload["metrics"].keys())
