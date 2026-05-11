import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def _make_mock_result():
    from simulation.orchestrator import SimulationResult
    agent = MagicMock()
    agent.name = "Agent1"
    agent.archetype = "TruthSeeker"
    state = MagicMock()
    state.stance = 0.85
    state.emotion = "determined"
    return SimulationResult(
        verdict="Society reaches broad consensus in support",
        confidence=0.68,
        distribution={"support": 0.68, "oppose": 0.22, "undecided": 0.10},
        top_agents=[{"agent": agent, "state": state}],
        narrative="Debate concluded.",
        counterfactuals=[],
        report={},
    )


def _run_cli(args):
    import io
    import importlib
    # Reload cli module fresh each test to avoid cached state
    if "cli" in sys.modules:
        del sys.modules["cli"]
    import cli

    mock_result = _make_mock_result()
    output_buf = io.StringIO()

    with patch.object(sys, "argv", ["cli.py"] + args), \
         patch("simulation.orchestrator.run_simulation", new=AsyncMock(return_value=mock_result)), \
         patch("sys.stdout", new=output_buf):
        try:
            cli.main()
        except SystemExit:
            pass

    return output_buf.getvalue()


def test_cli_output_contains_verdict():
    out = _run_cli(["--scenario", "Test"])
    assert "consensus" in out.lower() or "Verdict" in out


def test_cli_defaults():
    """Defaults: agents=50, rounds=5."""
    import io
    if "cli" in sys.modules:
        del sys.modules["cli"]
    import cli

    captured = {}
    mock_result = _make_mock_result()

    async def cap(**kw):
        captured.update(kw)
        return mock_result

    with patch.object(sys, "argv", ["cli.py", "--scenario", "X"]), \
         patch("simulation.orchestrator.run_simulation", new=cap), \
         patch("sys.stdout", new=io.StringIO()):
        cli.main()

    assert captured.get("agent_count") == 50
    assert captured.get("rounds") == 5
