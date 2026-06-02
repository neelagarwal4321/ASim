import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def test_helpers_are_importable():
    from tasks.simulation_tasks import _persist_result, _update_status
    assert callable(_persist_result)
    assert callable(_update_status)


@pytest.mark.asyncio
async def test_persist_result_adds_row_and_updates_status():
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.add = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("db.database.AsyncSessionLocal", return_value=mock_session):
        from tasks.simulation_tasks import _persist_result
        await _persist_result("sim-001", {
            "verdict": "Majority support",
            "confidence": 0.72,
            "distribution": {"support": 0.6, "oppose": 0.25, "undecided": 0.15},
            "narrative": "Society shifted toward acceptance.",
        })

    mock_session.add.assert_called_once()
    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_status_calls_execute_and_commit():
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    with patch("db.database.AsyncSessionLocal", return_value=mock_session):
        from tasks.simulation_tasks import _update_status
        await _update_status("sim-001", "failed")

    mock_session.execute.assert_called_once()
    mock_session.commit.assert_called_once()
