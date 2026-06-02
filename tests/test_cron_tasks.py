"""Unit tests for cron_tasks helper logic (no DB/Redis hits)."""
import datetime


def test_extract_sim_ids():
    keys = ['apikey:sim-1', 'apikey:sim-2', 'other:key']
    ids = [k.replace('apikey:', '') for k in keys if k.startswith('apikey:')]
    assert ids == ['sim-1', 'sim-2']


def test_watchdog_stale_detection():
    # age > max_dur is stale
    updated_at = datetime.datetime.utcnow() - datetime.timedelta(hours=3)
    age = (datetime.datetime.utcnow() - updated_at).total_seconds()
    assert age > 1800  # free tier max = 1800s


def test_extract_sim_ids_empty():
    keys = ['other:key', 'ratelimit:sim:active:user-1']
    ids = [k.replace('apikey:', '') for k in keys if k.startswith('apikey:')]
    assert ids == []


def test_is_stale_helper():
    """Test the _is_stale helper directly via import."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

    from tasks.cron_tasks import _is_stale

    # 2 hours old, max 1800s (30 min) — stale
    old_time = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    assert _is_stale(old_time, 1800) is True

    # 10 seconds old, max 3600s — not stale
    fresh_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=10)
    assert _is_stale(fresh_time, 3600) is False


def test_extract_sim_ids_helper():
    """Test the _extract_sim_ids_from_api_keys helper directly via import."""
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

    from tasks.cron_tasks import _extract_sim_ids_from_api_keys

    keys = ['apikey:abc-123', 'apikey:def-456', 'session:xyz', 'ratelimit:sim:active:user1']
    result = _extract_sim_ids_from_api_keys(keys)
    assert result == ['abc-123', 'def-456']

    assert _extract_sim_ids_from_api_keys([]) == []
