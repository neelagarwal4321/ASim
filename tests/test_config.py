import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))

def test_settings_defaults():
    from config import settings
    assert settings.llm_provider in ("ollama", "anthropic")
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.fastapi_port == 8000
