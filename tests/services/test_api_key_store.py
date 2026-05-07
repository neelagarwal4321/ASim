import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import fakeredis
from unittest.mock import patch
from services.api_key_store import store_api_key, retrieve_api_key, delete_api_key


def _fake():
    return fakeredis.FakeRedis(decode_responses=False)


def test_store_retrieve_roundtrip():
    fake = _fake()
    with patch("services.api_key_store.redis.from_url", return_value=fake):
        store_api_key("s1", "sk-secret")
        assert retrieve_api_key("s1") == "sk-secret"


def test_retrieve_missing_returns_none():
    fake = _fake()
    with patch("services.api_key_store.redis.from_url", return_value=fake):
        assert retrieve_api_key("missing") is None


def test_delete_removes_key():
    fake = _fake()
    with patch("services.api_key_store.redis.from_url", return_value=fake):
        store_api_key("s2", "sk-x")
        delete_api_key("s2")
        assert retrieve_api_key("s2") is None


def test_stored_value_is_encrypted():
    fake = _fake()
    with patch("services.api_key_store.redis.from_url", return_value=fake):
        store_api_key("s3", "sk-plain")
    raw = fake.get("sim:s3:apikey")
    assert b"sk-plain" not in raw
