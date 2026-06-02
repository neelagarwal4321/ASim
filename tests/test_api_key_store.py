def test_api_key_uses_apikey_prefix(monkeypatch):
    stored_keys = {}
    class FakeRedis:
        def setex(self, key, ttl, val): stored_keys[key] = val
        def get(self, key): return stored_keys.get(key)
        def delete(self, key): stored_keys.pop(key, None)
    monkeypatch.setattr('services.api_key_store.redis.from_url', lambda *a, **kw: FakeRedis())
    from services.api_key_store import store_api_key, retrieve_api_key
    store_api_key('sim-123', 'sk-ant-test')
    assert any(k.startswith('apikey:') for k in stored_keys), f"Expected apikey: prefix, got: {list(stored_keys.keys())}"
    assert retrieve_api_key('sim-123') == 'sk-ant-test'
