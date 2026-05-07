import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import pytest
from unittest.mock import AsyncMock, patch
from simulation.orchestrator import RoundResult
from output.narrative_synthesizer import generate_narrative


def _logs(n=3):
    return [RoundResult(round_num=i, actions=[],
                        stance_distribution={"support": 0.5, "oppose": 0.3, "undecided": 0.2})
            for i in range(1, n + 1)]


def _verdict():
    return {"verdict": "consensus", "confidence": 0.7,
            "distribution": {"support": 0.7, "oppose": 0.2, "undecided": 0.1}}


async def test_returns_llm_text():
    with patch("output.narrative_synthesizer.llm_executor") as m:
        m.complete = AsyncMock(return_value="  Result.  ")
        result = await generate_narrative("Test", _logs(), _verdict())
    assert result == "Result."


async def test_fallback_on_llm_failure():
    with patch("output.narrative_synthesizer.llm_executor") as m:
        m.complete = AsyncMock(side_effect=RuntimeError("down"))
        result = await generate_narrative("Vaccines", _logs(), _verdict())
    assert isinstance(result, str) and len(result) > 10


async def test_passes_api_key():
    with patch("output.narrative_synthesizer.llm_executor") as m:
        m.complete = AsyncMock(return_value="ok")
        await generate_narrative("S", _logs(), _verdict(), api_key="sk-x")
    assert m.complete.call_args.kwargs.get("api_key") == "sk-x"
