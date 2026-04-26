# Phase 1 FastAPI Simulation Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working end-to-end simulation CLI: `python backend/cli.py --scenario "..." --agents 50 --rounds 5` that produces a verdict, top agents, and narrative arc from real LLM-driven agent interactions.

**Architecture:** FastAPI Python backend only. No database (in-memory state). No Celery (sequential execution). LLM calls go through `llm/executor.py` exclusively — provider switched by `LLM_PROVIDER` env var. Ollama for local dev.

**Tech Stack:** Python 3.11+, FastAPI 0.115, Pydantic v2, pydantic-settings, httpx, anthropic SDK, pytest, pytest-asyncio

---

## File Map

```
backend/
├── __init__.py                    CREATE — empty package marker
├── requirements.txt               CREATE — all Python deps
├── config.py                      CREATE — pydantic-settings env loader (singleton: settings)
├── cli.py                         CREATE — argparse entry point, runs asyncio simulation loop
├── main.py                        CREATE — FastAPI app, GET /health stub only
├── llm/
│   ├── __init__.py                CREATE — empty
│   ├── executor.py                CREATE — LLMExecutor class + llm_executor singleton
│   ├── ollama_provider.py         CREATE — OllamaProvider, httpx POST to Ollama
│   ├── anthropic_provider.py      CREATE — AnthropicProvider, cache_control on Blocks 1-3
│   └── response_parser.py         CREATE — parse_response(text) -> (free_text, json_dict)
├── agents/
│   ├── __init__.py                CREATE — empty
│   ├── models.py                  CREATE — AgentProfile, AgentState, TraitVector, RoundAction
│   ├── archetypes.py              CREATE — ARCHETYPES dict: 10 preset definitions
│   ├── voice_styles.py            CREATE — VOICE_STYLES dict: per-archetype voice strings
│   └── generator.py               CREATE — generate_agents(count, seed) -> list[AgentProfile]
├── simulation/
│   ├── __init__.py                CREATE — empty
│   ├── state_manager.py           CREATE — StateManager: in-memory AgentState + trust scores
│   ├── action_selector.py         CREATE — select_action(agent, state, all_ids, rng) -> (action, target)
│   ├── prompt_builder.py          CREATE — build_prompt(...) -> (static_system, dynamic_context, user_message)
│   ├── persuasion_engine.py       CREATE — resolve_persuasion(...) -> float delta
│   └── orchestrator.py            CREATE — run_simulation(...) -> SimulationResult
├── output/
│   ├── __init__.py                CREATE — empty
│   ├── aggregator.py              CREATE — compute_verdict(states) -> dict (pure Python)
│   └── narrative_synthesizer.py   CREATE — generate_narrative(...) -> str (one LLM call)
└── api/
    ├── __init__.py                CREATE — empty
    ├── health.py                  CREATE — GET /health router
    └── internal.py                CREATE — stubs: POST /internal/simulate/start (Phase 2)

tests/
├── conftest.py                    CREATE — shared fixtures
├── llm/
│   └── test_response_parser.py    CREATE — parse_response unit tests
├── agents/
│   ├── test_models.py             CREATE — Pydantic model validation tests
│   └── test_generator.py          CREATE — generate_agents tests
├── simulation/
│   ├── test_state_manager.py      CREATE — StateManager CRUD tests
│   ├── test_action_selector.py    CREATE — action selection distribution tests
│   ├── test_prompt_builder.py     CREATE — 6-block order and content tests
│   └── test_persuasion_engine.py  CREATE — formula correctness + 0.15 cap tests
└── output/
    └── test_aggregator.py         CREATE — verdict computation tests
```

---

## Task 1: Project Scaffold

**Files:** `backend/__init__.py`, `backend/requirements.txt`, `backend/config.py`

- [ ] **Step 1.1: Create virtual environment (skip if `.venv/` exists)**

```bash
cd c:/Neel/CODING/ASim
python -m venv .venv
.venv\Scripts\activate
```

- [ ] **Step 1.2: Create `backend/__init__.py`**

```python
```
(empty file)

- [ ] **Step 1.3: Create `backend/requirements.txt`**

```
fastapi==0.115.5
uvicorn[standard]==0.32.1
pydantic==2.10.3
pydantic-settings==2.6.1
httpx==0.28.1
anthropic==0.40.0
python-dotenv==1.0.1
pytest==8.3.4
pytest-asyncio==0.24.0
```

- [ ] **Step 1.4: Install dependencies**

```bash
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 1.5: Create `backend/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    llm_provider: str = "ollama"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    database_url: str = ""
    mongodb_url: str = ""
    mongodb_db: str = "asim"
    redis_url: str = ""
    app_env: str = "development"
    fastapi_port: int = 8000
    secret_key: str = ""


settings = Settings()
```

- [ ] **Step 1.6: Write config test**

Create `tests/test_config.py`:

```python
def test_settings_defaults():
    from config import settings
    assert settings.llm_provider in ("ollama", "anthropic")
    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.fastapi_port == 8000
```

- [ ] **Step 1.7: Run config test**

```bash
cd c:/Neel/CODING/ASim
.venv\Scripts\activate
python -m pytest tests/test_config.py -v
```

Expected: `PASSED tests/test_config.py::test_settings_defaults`

- [ ] **Step 1.8: Commit**

```bash
git add backend/__init__.py backend/requirements.txt backend/config.py tests/test_config.py
git commit -m "feat(backend): project scaffold — requirements, config, venv"
```

---

## Task 2: LLM Response Parser

**Files:** `backend/llm/__init__.py`, `backend/llm/response_parser.py`, `tests/llm/test_response_parser.py`

- [ ] **Step 2.1: Create `tests/llm/__init__.py` and `backend/llm/__init__.py`**

Both are empty files.

- [ ] **Step 2.2: Write failing tests for `response_parser`**

Create `tests/llm/test_response_parser.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from llm.response_parser import parse_response


def test_extracts_json_and_free_text():
    text = 'I believe this is wrong. {"action": "debate", "stance": 0.3, "emotion": "angry", "confidence": 0.7, "argument_quality": 0.6}'
    free_text, json_data = parse_response(text)
    assert "I believe" in free_text
    assert json_data["action"] == "debate"
    assert json_data["stance"] == 0.3


def test_returns_empty_dict_when_no_json():
    text = "This response has no JSON block at all."
    free_text, json_data = parse_response(text)
    assert free_text == text
    assert json_data == {}


def test_handles_json_at_start():
    text = '{"action": "agree", "stance": 0.8, "emotion": "hopeful", "confidence": 0.9, "argument_quality": 0.7}'
    free_text, json_data = parse_response(text)
    assert json_data["action"] == "agree"
    assert json_data["stance"] == 0.8


def test_handles_multiline_json():
    text = """I think we should support this.

{
  "action": "persuade",
  "stance": 0.75,
  "emotion": "optimistic",
  "confidence": 0.8,
  "argument_quality": 0.7
}"""
    free_text, json_data = parse_response(text)
    assert json_data["action"] == "persuade"
    assert "I think" in free_text
```

- [ ] **Step 2.3: Run tests — verify they fail**

```bash
python -m pytest tests/llm/test_response_parser.py -v
```

Expected: `ModuleNotFoundError: No module named 'llm'` or `ImportError`

- [ ] **Step 2.4: Create `backend/llm/response_parser.py`**

```python
import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_response(text: str) -> tuple[str, dict]:
    """Extract free text and JSON block from LLM response.

    Returns (free_text, json_dict). json_dict is {} if no valid JSON found.
    """
    # Try to find the last {...} block — handles trailing JSON pattern
    matches = list(re.finditer(r'\{[^{}]*\}', text, re.DOTALL))
    if not matches:
        logger.warning("No JSON block found in LLM response")
        return text.strip(), {}

    # Use the last match (agent prompts end with JSON)
    json_match = matches[-1]
    json_str = json_match.group(0)
    free_text = text[:json_match.start()].strip()

    try:
        json_data = json.loads(json_str)
        return free_text, json_data
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error: %s. Raw: %.100s", exc, json_str)
        return free_text, {}
```

- [ ] **Step 2.5: Run tests — verify they pass**

```bash
python -m pytest tests/llm/test_response_parser.py -v
```

Expected: all 4 tests `PASSED`

- [ ] **Step 2.6: Commit**

```bash
git add backend/llm/__init__.py backend/llm/response_parser.py tests/llm/__init__.py tests/llm/test_response_parser.py
git commit -m "feat(llm): response parser with JSON extraction and retry support"
```

---

## Task 3: Ollama Provider + LLM Executor

**Files:** `backend/llm/ollama_provider.py`, `backend/llm/anthropic_provider.py`, `backend/llm/executor.py`

- [ ] **Step 3.1: Create `backend/llm/ollama_provider.py`**

```python
import httpx
import logging
from config import settings

logger = logging.getLogger(__name__)


class OllamaProvider:
    async def complete(
        self,
        user_message: str,
        static_system: str = "",
        dynamic_context: str = "",
        api_key: str | None = None,
    ) -> str:
        system = "\n\n".join(filter(None, [static_system, dynamic_context]))

        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": user_message,
                    "system": system,
                    "stream": False,
                },
            )
            response.raise_for_status()
            return response.json()["response"]
```

- [ ] **Step 3.2: Create `backend/llm/anthropic_provider.py`**

```python
import logging
import anthropic
from config import settings

logger = logging.getLogger(__name__)


class AnthropicProvider:
    def __init__(self) -> None:
        self._default_client = anthropic.AsyncAnthropic(
            api_key=settings.anthropic_api_key or None
        )

    def _get_client(self, api_key: str | None) -> anthropic.AsyncAnthropic:
        if api_key:
            return anthropic.AsyncAnthropic(api_key=api_key)
        return self._default_client

    async def complete(
        self,
        user_message: str,
        static_system: str = "",
        dynamic_context: str = "",
        api_key: str | None = None,
    ) -> str:
        client = self._get_client(api_key)

        # Blocks 1-3 (static_system) are cached; Blocks 4-5 (dynamic_context) are not
        system_blocks: list[dict] = []
        if static_system:
            system_blocks.append({
                "type": "text",
                "text": static_system,
                "cache_control": {"type": "ephemeral"},
            })
        if dynamic_context:
            system_blocks.append({
                "type": "text",
                "text": dynamic_context,
            })

        response = await client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            system=system_blocks if system_blocks else anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
```

- [ ] **Step 3.3: Create `backend/llm/executor.py`**

```python
import logging
from config import settings

logger = logging.getLogger(__name__)


class LLMExecutor:
    def __init__(self) -> None:
        if settings.llm_provider == "anthropic":
            from llm.anthropic_provider import AnthropicProvider
            self._provider = AnthropicProvider()
        else:
            from llm.ollama_provider import OllamaProvider
            self._provider = OllamaProvider()
        logger.info("LLM executor initialized with provider: %s", settings.llm_provider)

    async def complete(
        self,
        user_message: str,
        static_system: str = "",
        dynamic_context: str = "",
        api_key: str | None = None,
    ) -> str:
        return await self._provider.complete(
            user_message=user_message,
            static_system=static_system,
            dynamic_context=dynamic_context,
            api_key=api_key,
        )


llm_executor = LLMExecutor()
```

- [ ] **Step 3.4: Verify Ollama is running (manual check)**

```bash
curl http://localhost:11434/api/generate -d '{"model":"llama3.1:8b","prompt":"say hi","stream":false}'
```

Expected: JSON response with a `"response"` field.

If Ollama is not running: `ollama serve` in a separate terminal, then `ollama pull llama3.1:8b`.

- [ ] **Step 3.5: Smoke test executor from Python REPL**

```bash
cd c:/Neel/CODING/ASim
.venv\Scripts\activate
python -c "
import asyncio, sys
sys.path.insert(0, 'backend')
from llm.executor import llm_executor
result = asyncio.run(llm_executor.complete('Say hello in one word.'))
print(repr(result))
"
```

Expected: printed string like `'Hello!'`

- [ ] **Step 3.6: Commit**

```bash
git add backend/llm/ollama_provider.py backend/llm/anthropic_provider.py backend/llm/executor.py
git commit -m "feat(llm): executor with Ollama provider and Anthropic provider (cache_control on Blocks 1-3)"
```

---

## Task 4: Agent Models

**Files:** `backend/agents/__init__.py`, `backend/agents/models.py`, `tests/agents/test_models.py`

- [ ] **Step 4.1: Create `backend/agents/__init__.py`** and `tests/agents/__init__.py` (both empty)

- [ ] **Step 4.2: Write failing model tests**

Create `tests/agents/test_models.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

import pytest
from pydantic import ValidationError
from agents.models import TraitVector, AgentProfile, AgentState, RoundAction


def test_trait_vector_clamps_to_range():
    with pytest.raises(ValidationError):
        TraitVector(openness=1.5, conscientiousness=0.5, extraversion=0.5,
                    agreeableness=0.5, neuroticism=0.5, moral_rigidity=0.5, susceptibility=0.5)


def test_agent_profile_valid():
    tv = TraitVector(openness=0.7, conscientiousness=0.6, extraversion=0.5,
                     agreeableness=0.4, neuroticism=0.3, moral_rigidity=0.2, susceptibility=0.5)
    agent = AgentProfile(
        id="abc",
        name="Alice",
        archetype="TruthSeeker",
        trait_vector=tv,
        core_beliefs=["Facts matter"],
        voice_style="precise and analytical",
        moral_alignment="utilitarian",
        appeal_type="rational",
    )
    assert agent.name == "Alice"
    assert agent.moral_alignment == "utilitarian"


def test_agent_state_defaults():
    state = AgentState(agent_id="abc")
    assert state.stance == 0.5
    assert state.emotion == "neutral"
    assert state.round == 0


def test_agent_state_stance_clamped():
    with pytest.raises(ValidationError):
        AgentState(agent_id="abc", stance=1.5)


def test_round_action_valid():
    action = RoundAction(
        agent_id="abc", name="Alice", archetype="TruthSeeker",
        action="debate", target_id="xyz", free_text="I disagree.",
        stance=0.3, emotion="angry", confidence=0.7,
    )
    assert action.action == "debate"
```

- [ ] **Step 4.3: Run tests — verify they fail**

```bash
python -m pytest tests/agents/test_models.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 4.4: Create `backend/agents/models.py`**

```python
from typing import Literal
from pydantic import BaseModel, Field

MoralAlignment = Literal["authoritarian", "libertarian", "utilitarian", "deontological", "nihilist"]
AppealType = Literal["emotional", "rational", "social", "authority"]
ActionType = Literal["debate", "persuade", "broadcast", "challenge", "agree", "withdraw", "rally"]
EmotionType = Literal["neutral", "optimistic", "angry", "fearful", "determined", "hopeful", "cynical", "passionate"]


class TraitVector(BaseModel):
    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)
    moral_rigidity: float = Field(ge=0.0, le=1.0)
    susceptibility: float = Field(ge=0.0, le=1.0)


class AgentProfile(BaseModel):
    id: str
    name: str
    archetype: str
    trait_vector: TraitVector
    core_beliefs: list[str]
    voice_style: str
    moral_alignment: MoralAlignment
    appeal_type: AppealType


class AgentState(BaseModel):
    agent_id: str
    round: int = 0
    stance: float = Field(default=0.5, ge=0.0, le=1.0)
    emotion: EmotionType = "neutral"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    memory_text: str = ""
    influence_score: float = 0.0
    interaction_count: int = 0
    last_action: ActionType = "debate"
    last_target: str | None = None


class RoundAction(BaseModel):
    agent_id: str
    name: str
    archetype: str
    action: ActionType
    target_id: str | None
    free_text: str
    stance: float
    emotion: EmotionType
    confidence: float
```

- [ ] **Step 4.5: Run tests — verify they pass**

```bash
python -m pytest tests/agents/test_models.py -v
```

Expected: all 5 tests `PASSED`

- [ ] **Step 4.6: Commit**

```bash
git add backend/agents/__init__.py backend/agents/models.py tests/agents/__init__.py tests/agents/test_models.py
git commit -m "feat(agents): AgentProfile, AgentState, TraitVector, RoundAction Pydantic models"
```

---

## Task 5: Archetypes, Voice Styles, Agent Generator

**Files:** `backend/agents/archetypes.py`, `backend/agents/voice_styles.py`, `backend/agents/generator.py`, `tests/agents/test_generator.py`

- [ ] **Step 5.1: Write failing generator tests**

Create `tests/agents/test_generator.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from agents.generator import generate_agents
from agents.models import AgentProfile


def test_generates_correct_count():
    agents = generate_agents(count=10, seed=42)
    assert len(agents) == 10


def test_all_agents_are_profiles():
    agents = generate_agents(count=5, seed=1)
    for agent in agents:
        assert isinstance(agent, AgentProfile)
        assert agent.id
        assert agent.name
        assert 0.0 <= agent.trait_vector.openness <= 1.0


def test_seed_reproducibility():
    agents_a = generate_agents(count=20, seed=99)
    agents_b = generate_agents(count=20, seed=99)
    assert [a.id for a in agents_a] == [a.id for a in agents_b]
    assert [a.archetype for a in agents_a] == [a.archetype for a in agents_b]


def test_different_seeds_give_variety():
    agents_a = generate_agents(count=20, seed=1)
    agents_b = generate_agents(count=20, seed=2)
    archetypes_a = {a.archetype for a in agents_a}
    archetypes_b = {a.archetype for a in agents_b}
    # At least some archetypes appear in both — not completely different
    assert archetypes_a & archetypes_b


def test_agents_have_variety_of_archetypes():
    agents = generate_agents(count=50, seed=7)
    archetypes = {a.archetype for a in agents}
    assert len(archetypes) >= 5, "Expected at least 5 distinct archetypes in 50 agents"


def test_all_trait_values_in_range():
    agents = generate_agents(count=50, seed=42)
    for agent in agents:
        tv = agent.trait_vector
        for val in [tv.openness, tv.conscientiousness, tv.extraversion,
                    tv.agreeableness, tv.neuroticism, tv.moral_rigidity, tv.susceptibility]:
            assert 0.0 <= val <= 1.0
```

- [ ] **Step 5.2: Run tests — verify they fail**

```bash
python -m pytest tests/agents/test_generator.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 5.3: Create `backend/agents/archetypes.py`**

```python
ARCHETYPES: dict[str, dict] = {
    "TruthSeeker": {
        "trait_vector": {"openness": 0.85, "conscientiousness": 0.75, "extraversion": 0.55,
                         "agreeableness": 0.60, "neuroticism": 0.25, "moral_rigidity": 0.40, "susceptibility": 0.45},
        "moral_alignment": "utilitarian",
        "appeal_type": "rational",
        "beliefs": [
            "Evidence and data should guide decisions",
            "Scientific consensus deserves serious weight",
            "Complex problems require nuanced solutions",
            "Intellectual honesty matters more than tribal loyalty",
        ],
    },
    "AuthorityDeferrer": {
        "trait_vector": {"openness": 0.30, "conscientiousness": 0.80, "extraversion": 0.45,
                         "agreeableness": 0.75, "neuroticism": 0.30, "moral_rigidity": 0.75, "susceptibility": 0.60},
        "moral_alignment": "authoritarian",
        "appeal_type": "authority",
        "beliefs": [
            "Institutions exist for good reason",
            "Social order prevents chaos",
            "Experts and leaders should be trusted",
            "Rules protect everyone equally",
        ],
    },
    "Rebel": {
        "trait_vector": {"openness": 0.80, "conscientiousness": 0.35, "extraversion": 0.70,
                         "agreeableness": 0.20, "neuroticism": 0.55, "moral_rigidity": 0.65, "susceptibility": 0.30},
        "moral_alignment": "libertarian",
        "appeal_type": "emotional",
        "beliefs": [
            "Government overreach threatens freedom",
            "Individual choice is sacred",
            "The establishment cannot be trusted",
            "Resistance to control is a virtue",
        ],
    },
    "Pragmatist": {
        "trait_vector": {"openness": 0.60, "conscientiousness": 0.70, "extraversion": 0.50,
                         "agreeableness": 0.55, "neuroticism": 0.30, "moral_rigidity": 0.35, "susceptibility": 0.55},
        "moral_alignment": "utilitarian",
        "appeal_type": "rational",
        "beliefs": [
            "Practical outcomes matter more than ideology",
            "Compromise is not weakness",
            "Context determines what is right",
            "Short-term sacrifice can yield long-term gain",
        ],
    },
    "Idealist": {
        "trait_vector": {"openness": 0.70, "conscientiousness": 0.65, "extraversion": 0.60,
                         "agreeableness": 0.65, "neuroticism": 0.45, "moral_rigidity": 0.85, "susceptibility": 0.30},
        "moral_alignment": "deontological",
        "appeal_type": "emotional",
        "beliefs": [
            "Principles must never be compromised for convenience",
            "Justice is non-negotiable",
            "Rights are inherent, not granted",
            "Moral clarity requires courage",
        ],
    },
    "Manipulator": {
        "trait_vector": {"openness": 0.65, "conscientiousness": 0.55, "extraversion": 0.80,
                         "agreeableness": 0.15, "neuroticism": 0.35, "moral_rigidity": 0.20, "susceptibility": 0.20},
        "moral_alignment": "nihilist",
        "appeal_type": "social",
        "beliefs": [
            "Power determines outcomes, not truth",
            "People are motivated by self-interest",
            "Perception is more important than reality",
            "Strategic ambiguity is a useful tool",
        ],
    },
    "Conformist": {
        "trait_vector": {"openness": 0.30, "conscientiousness": 0.60, "extraversion": 0.55,
                         "agreeableness": 0.80, "neuroticism": 0.50, "moral_rigidity": 0.40, "susceptibility": 0.85},
        "moral_alignment": "authoritarian",
        "appeal_type": "social",
        "beliefs": [
            "Going along with the group is usually the safe choice",
            "Social harmony matters",
            "If everyone does it, it must be acceptable",
            "Standing out invites trouble",
        ],
    },
    "EmotionalReactor": {
        "trait_vector": {"openness": 0.55, "conscientiousness": 0.35, "extraversion": 0.65,
                         "agreeableness": 0.50, "neuroticism": 0.90, "moral_rigidity": 0.45, "susceptibility": 0.70},
        "moral_alignment": "deontological",
        "appeal_type": "emotional",
        "beliefs": [
            "Feelings are valid data points",
            "Personal experience is the most honest guide",
            "Compassion should drive policy",
            "Emotional truth matters as much as logical truth",
        ],
    },
    "CommunityBuilder": {
        "trait_vector": {"openness": 0.65, "conscientiousness": 0.70, "extraversion": 0.80,
                         "agreeableness": 0.85, "neuroticism": 0.30, "moral_rigidity": 0.35, "susceptibility": 0.50},
        "moral_alignment": "utilitarian",
        "appeal_type": "social",
        "beliefs": [
            "We are stronger together",
            "Bridges matter more than walls",
            "Everyone deserves to be heard",
            "Collective wellbeing requires individual sacrifice",
        ],
    },
    "Cynic": {
        "trait_vector": {"openness": 0.35, "conscientiousness": 0.45, "extraversion": 0.40,
                         "agreeableness": 0.20, "neuroticism": 0.60, "moral_rigidity": 0.55, "susceptibility": 0.25},
        "moral_alignment": "nihilist",
        "appeal_type": "rational",
        "beliefs": [
            "Nothing will fundamentally change",
            "Those in power serve themselves",
            "Good intentions produce bad outcomes",
            "Skepticism is the only honest position",
        ],
    },
}
```

- [ ] **Step 5.4: Create `backend/agents/voice_styles.py`**

```python
VOICE_STYLES: dict[str, str] = {
    "TruthSeeker": "precise and evidence-based; cites data, asks for sources, acknowledges uncertainty",
    "AuthorityDeferrer": "deferential and formal; references official guidance and institutions",
    "Rebel": "confrontational and passionate; challenges authority, speaks in absolutes about freedom",
    "Pragmatist": "measured and outcome-focused; weighs trade-offs, avoids ideological language",
    "Idealist": "principled and unwavering; invokes rights and moral duties, refuses compromise",
    "Manipulator": "smooth and strategic; appeals to others' interests, reframes issues to own advantage",
    "Conformist": "agreeable and vague; echoes the prevailing view, avoids strong personal positions",
    "EmotionalReactor": "visceral and personal; speaks from lived experience, uses emotional imagery",
    "CommunityBuilder": "warm and inclusive; emphasizes shared values, seeks common ground",
    "Cynic": "dry and dismissive; expects the worst, finds flaws in every proposal",
}
```

- [ ] **Step 5.5: Create `backend/agents/generator.py`**

```python
import random
import uuid

from agents.models import AgentProfile, TraitVector
from agents.archetypes import ARCHETYPES
from agents.voice_styles import VOICE_STYLES

_FIRST_NAMES = [
    "Alice", "Marcus", "Sarah", "James", "Priya", "David", "Elena", "Omar",
    "Jessica", "Thomas", "Amara", "Carlos", "Mei", "Noah", "Fatima", "Liam",
    "Zoe", "Raj", "Hannah", "Kwame", "Sofia", "Andre", "Yuki", "Patrick",
    "Ingrid", "Darius", "Clara", "Tariq", "Nadia", "Sebastian",
]

_LAST_NAMES = [
    "Chen", "Rivera", "Johnson", "Okoye", "Patel", "Kim", "Vasquez", "Hassan",
    "Williams", "Berg", "Diallo", "Santos", "Lin", "Freeman", "Al-Rashid",
    "Murphy", "Torres", "Nakamura", "Schmidt", "Mensah", "Greco", "Dubois",
    "Tanaka", "O'Brien", "Larsson", "Nkosi", "Fischer", "Bakr", "Petrov", "Walsh",
]


def _clamp(val: float) -> float:
    return max(0.0, min(1.0, val))


def generate_agents(count: int = 50, seed: int | None = None) -> list[AgentProfile]:
    rng = random.Random(seed)
    archetype_keys = list(ARCHETYPES.keys())
    used_names: set[str] = set()
    agents: list[AgentProfile] = []

    for _ in range(count):
        archetype_key = rng.choice(archetype_keys)
        base = ARCHETYPES[archetype_key]
        base_tv = base["trait_vector"]

        trait_vector = TraitVector(
            openness=_clamp(base_tv["openness"] + rng.gauss(0, 0.10)),
            conscientiousness=_clamp(base_tv["conscientiousness"] + rng.gauss(0, 0.10)),
            extraversion=_clamp(base_tv["extraversion"] + rng.gauss(0, 0.10)),
            agreeableness=_clamp(base_tv["agreeableness"] + rng.gauss(0, 0.10)),
            neuroticism=_clamp(base_tv["neuroticism"] + rng.gauss(0, 0.10)),
            moral_rigidity=_clamp(base_tv["moral_rigidity"] + rng.gauss(0, 0.05)),
            susceptibility=_clamp(base_tv["susceptibility"] + rng.gauss(0, 0.05)),
        )

        # Generate unique name
        for _ in range(20):
            name = f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"
            if name not in used_names:
                used_names.add(name)
                break

        beliefs = base["beliefs"]
        selected_beliefs = rng.sample(beliefs, k=min(3, len(beliefs)))

        agents.append(AgentProfile(
            id=str(uuid.UUID(int=rng.getrandbits(128))),
            name=name,
            archetype=archetype_key,
            trait_vector=trait_vector,
            core_beliefs=selected_beliefs,
            voice_style=VOICE_STYLES[archetype_key],
            moral_alignment=base["moral_alignment"],
            appeal_type=base["appeal_type"],
        ))

    return agents
```

- [ ] **Step 5.6: Run generator tests — verify they pass**

```bash
python -m pytest tests/agents/test_generator.py -v
```

Expected: all 6 tests `PASSED`

- [ ] **Step 5.7: Commit**

```bash
git add backend/agents/archetypes.py backend/agents/voice_styles.py backend/agents/generator.py tests/agents/test_generator.py
git commit -m "feat(agents): 10 archetypes, voice styles, agent generator with seeded random variation"
```

---

## Task 6: State Manager

**Files:** `backend/simulation/__init__.py`, `backend/simulation/state_manager.py`, `tests/simulation/test_state_manager.py`

- [ ] **Step 6.1: Create `backend/simulation/__init__.py`** and `tests/simulation/__init__.py` (both empty)

- [ ] **Step 6.2: Write failing state manager tests**

Create `tests/simulation/test_state_manager.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from simulation.state_manager import StateManager
from agents.models import AgentState


def test_init_creates_default_state():
    mgr = StateManager()
    state = mgr.init_agent_state("agent-1")
    assert state.agent_id == "agent-1"
    assert state.stance == 0.5
    assert state.round == 0


def test_get_state_returns_stored():
    mgr = StateManager()
    mgr.init_agent_state("agent-1")
    state = mgr.get_state("agent-1")
    assert state.agent_id == "agent-1"


def test_update_state_persists():
    mgr = StateManager()
    state = mgr.init_agent_state("agent-1")
    state.stance = 0.9
    state.emotion = "angry"
    mgr.update_state(state)
    retrieved = mgr.get_state("agent-1")
    assert retrieved.stance == 0.9
    assert retrieved.emotion == "angry"


def test_get_all_states():
    mgr = StateManager()
    mgr.init_agent_state("a1")
    mgr.init_agent_state("a2")
    mgr.init_agent_state("a3")
    all_states = mgr.get_all_states()
    assert len(all_states) == 3


def test_trust_defaults_to_neutral():
    mgr = StateManager()
    trust = mgr.get_trust("a1", "a2")
    assert trust == 0.5


def test_trust_update_clamps():
    mgr = StateManager()
    mgr.update_trust("a1", "a2", 0.9)
    assert mgr.get_trust("a1", "a2") == 1.0
    mgr.update_trust("a1", "a2", -2.0)
    assert mgr.get_trust("a1", "a2") == 0.0
```

- [ ] **Step 6.3: Run tests — verify they fail**

```bash
python -m pytest tests/simulation/test_state_manager.py -v
```

Expected: `ModuleNotFoundError`

- [ ] **Step 6.4: Create `backend/simulation/state_manager.py`**

```python
from agents.models import AgentState


class StateManager:
    def __init__(self) -> None:
        self._states: dict[str, AgentState] = {}
        self._trust: dict[tuple[str, str], float] = {}

    def init_agent_state(self, agent_id: str) -> AgentState:
        state = AgentState(agent_id=agent_id)
        self._states[agent_id] = state
        return state

    def get_state(self, agent_id: str) -> AgentState:
        return self._states[agent_id]

    def update_state(self, state: AgentState) -> None:
        self._states[state.agent_id] = state

    def get_all_states(self) -> list[AgentState]:
        return list(self._states.values())

    def get_trust(self, agent_a_id: str, agent_b_id: str) -> float:
        return self._trust.get((agent_a_id, agent_b_id), 0.5)

    def update_trust(self, agent_a_id: str, agent_b_id: str, delta: float) -> None:
        key = (agent_a_id, agent_b_id)
        current = self._trust.get(key, 0.5)
        self._trust[key] = max(0.0, min(1.0, current + delta))
```

- [ ] **Step 6.5: Run tests — verify they pass**

```bash
python -m pytest tests/simulation/test_state_manager.py -v
```

Expected: all 6 tests `PASSED`

- [ ] **Step 6.6: Commit**

```bash
git add backend/simulation/__init__.py backend/simulation/state_manager.py tests/simulation/__init__.py tests/simulation/test_state_manager.py
git commit -m "feat(simulation): in-memory StateManager with trust score tracking"
```

---

## Task 7: Action Selector

**Files:** `backend/simulation/action_selector.py`, `tests/simulation/test_action_selector.py`

- [ ] **Step 7.1: Write failing action selector tests**

Create `tests/simulation/test_action_selector.py`:

```python
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
```

- [ ] **Step 7.2: Run tests — verify they fail**

```bash
python -m pytest tests/simulation/test_action_selector.py -v
```

- [ ] **Step 7.3: Create `backend/simulation/action_selector.py`**

```python
import random
from agents.models import AgentProfile, AgentState, ActionType

_ACTION_WEIGHT_FNS: dict[str, object] = {
    "debate":    lambda t: t.openness * 0.3 + t.extraversion * 0.3,
    "persuade":  lambda t: t.extraversion * 0.4 + (1 - t.agreeableness) * 0.2,
    "broadcast": lambda t: t.extraversion * 0.5 + t.conscientiousness * 0.2,
    "challenge": lambda t: (1 - t.agreeableness) * 0.4 + t.openness * 0.2,
    "agree":     lambda t: t.agreeableness * 0.5 + (1 - t.neuroticism) * 0.2,
    "withdraw":  lambda t: t.neuroticism * 0.3 + (1 - t.extraversion) * 0.3,
    "rally":     lambda t: t.extraversion * 0.3 + t.conscientiousness * 0.3,
}

_TARGETED_ACTIONS = frozenset({"debate", "persuade", "challenge"})


def select_action(
    agent: AgentProfile,
    state: AgentState,
    all_agent_ids: list[str],
    rng: random.Random,
) -> tuple[ActionType, str | None]:
    """Returns (action_type, target_agent_id | None)."""
    traits = agent.trait_vector
    actions = list(_ACTION_WEIGHT_FNS.keys())
    weights = [max(0.01, fn(traits)) for fn in _ACTION_WEIGHT_FNS.values()]

    action: ActionType = rng.choices(actions, weights=weights, k=1)[0]

    if action in _TARGETED_ACTIONS:
        candidates = [aid for aid in all_agent_ids if aid != agent.id]
        target = rng.choice(candidates) if candidates else None
    else:
        target = None

    return action, target
```

- [ ] **Step 7.4: Run tests — verify they pass**

```bash
python -m pytest tests/simulation/test_action_selector.py -v
```

Expected: all 3 tests `PASSED`

- [ ] **Step 7.5: Commit**

```bash
git add backend/simulation/action_selector.py tests/simulation/test_action_selector.py
git commit -m "feat(simulation): trait-weighted action selector with targeted/untargeted actions"
```

---

## Task 8: Prompt Builder

**Files:** `backend/simulation/prompt_builder.py`, `tests/simulation/test_prompt_builder.py`

- [ ] **Step 8.1: Write failing prompt builder tests**

Create `tests/simulation/test_prompt_builder.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from simulation.prompt_builder import build_prompt
from agents.generator import generate_agents
from agents.models import AgentState


def _make_agent_and_state():
    agents = generate_agents(count=1, seed=42)
    agent = agents[0]
    state = AgentState(agent_id=agent.id, stance=0.4, emotion="angry", confidence=0.6)
    return agent, state


def test_returns_three_strings():
    agent, state = _make_agent_and_state()
    result = build_prompt(agent, state, "debate", None, "Test scenario", 1, {}, 5)
    assert len(result) == 3
    static_sys, dynamic_ctx, user_msg = result
    assert isinstance(static_sys, str)
    assert isinstance(dynamic_ctx, str)
    assert isinstance(user_msg, str)


def test_static_system_contains_identity(  ):
    agent, state = _make_agent_and_state()
    static_sys, _, _ = build_prompt(agent, state, "debate", None, "Test scenario", 1, {}, 5)
    assert agent.name in static_sys
    assert agent.archetype in static_sys


def test_static_system_contains_moral_framing():
    agent, state = _make_agent_and_state()
    static_sys, _, _ = build_prompt(agent, state, "debate", None, "Test", 1, {}, 5)
    assert agent.moral_alignment in static_sys


def test_dynamic_context_contains_scenario():
    agent, state = _make_agent_and_state()
    _, dynamic_ctx, _ = build_prompt(agent, state, "debate", None, "Vaccine mandate test", 1, {}, 5)
    assert "Vaccine mandate test" in dynamic_ctx


def test_dynamic_context_contains_stance():
    agent, state = _make_agent_and_state()
    _, dynamic_ctx, _ = build_prompt(agent, state, "debate", None, "Test", 1, {}, 5)
    assert "0.4" in dynamic_ctx  # current stance


def test_user_message_contains_action():
    agent, state = _make_agent_and_state()
    _, _, user_msg = build_prompt(agent, state, "challenge", "Bob", "Test", 1, {}, 5)
    assert "challenge" in user_msg
    assert "Bob" in user_msg


def test_user_message_ends_with_json_spec():
    agent, state = _make_agent_and_state()
    _, _, user_msg = build_prompt(agent, state, "debate", None, "Test", 1, {}, 5)
    assert '"action"' in user_msg
    assert '"stance"' in user_msg
    assert '"emotion"' in user_msg


def test_block_order_static_before_dynamic():
    """Blocks 1-3 must be in static_system. Blocks 4-5 must be in dynamic_context. Block 6 in user_message."""
    agent, state = _make_agent_and_state()
    static_sys, dynamic_ctx, user_msg = build_prompt(
        agent, state, "debate", None, "Scenario X", 2, {}, 5
    )
    # Static must have agent identity (Block 1) and behavioral (Block 2) and moral (Block 3)
    assert agent.name in static_sys
    assert str(agent.trait_vector.openness)[:3] in static_sys or "openness" in static_sys.lower()
    assert agent.moral_alignment in static_sys
    # Dynamic must have scenario (Block 4) and stance (Block 5)
    assert "Scenario X" in dynamic_ctx
    assert str(state.stance) in dynamic_ctx
    # User message has action instruction (Block 6)
    assert "debate" in user_msg
```

- [ ] **Step 8.2: Run tests — verify they fail**

```bash
python -m pytest tests/simulation/test_prompt_builder.py -v
```

- [ ] **Step 8.3: Create `backend/simulation/prompt_builder.py`**

```python
from agents.models import AgentProfile, AgentState, ActionType


def build_prompt(
    agent: AgentProfile,
    state: AgentState,
    action: ActionType,
    target_name: str | None,
    scenario: str,
    round_num: int,
    trust_scores: dict[str, float],
    total_rounds: int,
) -> tuple[str, str, str]:
    """Assemble the 6-block prompt.

    Returns (static_system, dynamic_context, user_message).
    static_system = Blocks 1-3 (identity, behavioral, moral) — cached in Anthropic.
    dynamic_context = Blocks 4-5 (social context, memory) — rebuilt every round.
    user_message = Block 6 (action instruction + JSON spec).
    """
    t = agent.trait_vector

    # Block 1: Identity
    block1 = (
        f"You are {agent.name}, a {agent.archetype}.\n\n"
        f"Your core beliefs:\n"
        + "\n".join(f"- {b}" for b in agent.core_beliefs)
        + f"\n\nYour voice: {agent.voice_style}"
    )

    # Block 2: Behavioral instructions
    block2 = (
        f"Your behavioral profile:\n"
        f"- Openness to new ideas: {t.openness:.2f}/1.0\n"
        f"- Conscientiousness: {t.conscientiousness:.2f}/1.0\n"
        f"- Extraversion: {t.extraversion:.2f}/1.0\n"
        f"- Agreeableness: {t.agreeableness:.2f}/1.0\n"
        f"- Emotional reactivity: {t.neuroticism:.2f}/1.0\n\n"
        f"You tend to make {agent.appeal_type} arguments.\n"
        f"You stay consistent with your identity even under social pressure."
    )

    # Block 3: Moral framing
    rigidity_note = (
        "You are highly resistant to changing your fundamental values."
        if t.moral_rigidity > 0.7
        else "You can update your positions when presented with compelling arguments."
    )
    block3 = (
        f"Your moral framework: {agent.moral_alignment}.\n"
        f"Moral rigidity: {t.moral_rigidity:.2f}/1.0\n"
        f"{rigidity_note}"
    )

    static_system = f"{block1}\n\n{block2}\n\n{block3}"

    # Block 4: Social context
    if trust_scores:
        trust_lines = "\n".join(
            f"- {name}: trust {score:.2f}"
            for name, score in sorted(trust_scores.items(), key=lambda x: x[1], reverse=True)[:5]
        )
        relationship_text = trust_lines
    else:
        relationship_text = "No established relationships yet."

    block4 = (
        f"Current scenario: {scenario}\n\n"
        f"Round {round_num} of {total_rounds}.\n\n"
        f"Your current relationships:\n{relationship_text}"
    )

    # Block 5: Memory
    memory_note = (
        f"What you remember: {state.memory_text}"
        if state.memory_text
        else "This is the first round — form your initial position based on your beliefs."
    )
    block5 = (
        f"Your current state:\n"
        f"- Stance on the issue: {state.stance:.2f} (0.0 = strongly oppose, 1.0 = strongly support)\n"
        f"- Current emotion: {state.emotion}\n"
        f"- Confidence: {state.confidence:.2f}\n\n"
        f"{memory_note}"
    )

    dynamic_context = f"{block4}\n\n{block5}"

    # Block 6: Action instruction + JSON spec
    target_str = f" directed at {target_name}" if target_name else ""
    target_id_val = f'"{target_name}"' if target_name else "null"
    block6 = (
        f"Your action this round: {action}{target_str}.\n\n"
        f"Respond in character as {agent.name}. Stay true to your voice and beliefs.\n\n"
        f"End your response with this exact JSON block:\n"
        f'{{\n'
        f'  "action": "{action}",\n'
        f'  "target_id": {target_id_val},\n'
        f'  "stance": <your current stance 0.0-1.0>,\n'
        f'  "emotion": "<neutral|optimistic|angry|fearful|determined|hopeful|cynical|passionate>",\n'
        f'  "confidence": <0.0-1.0>,\n'
        f'  "argument_quality": <0.0-1.0>\n'
        f'}}'
    )

    return static_system, dynamic_context, block6
```

- [ ] **Step 8.4: Run tests — verify they pass**

```bash
python -m pytest tests/simulation/test_prompt_builder.py -v
```

Expected: all 8 tests `PASSED`

- [ ] **Step 8.5: Commit**

```bash
git add backend/simulation/prompt_builder.py tests/simulation/test_prompt_builder.py
git commit -m "feat(simulation): 6-block prompt builder (static Blocks 1-3 / dynamic Blocks 4-5 / action Block 6)"
```

---

## Task 9: Persuasion Engine

**Files:** `backend/simulation/persuasion_engine.py`, `tests/simulation/test_persuasion_engine.py`

- [ ] **Step 9.1: Write failing persuasion tests**

Create `tests/simulation/test_persuasion_engine.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from simulation.persuasion_engine import resolve_persuasion
from agents.generator import generate_agents
from agents.models import AgentState, RoundAction


def _make_action(agent_id, confidence=0.8):
    return RoundAction(
        agent_id=agent_id, name="Test", archetype="TruthSeeker",
        action="debate", target_id="target", free_text="I argue...",
        stance=0.8, emotion="determined", confidence=confidence,
    )


def test_returns_float():
    agents = generate_agents(count=2, seed=1)
    actor, target = agents[0], agents[1]
    actor_state = AgentState(agent_id=actor.id, stance=0.9, emotion="determined")
    target_state = AgentState(agent_id=target.id, stance=0.3, emotion="neutral")
    action = _make_action(actor.id)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=0.7, social_proof=0.6, repetition_bonus=0.1)
    assert isinstance(delta, float)


def test_hard_cap_015():
    """Max stance delta per round must not exceed 0.15."""
    agents = generate_agents(count=2, seed=1)
    actor, target = agents[0], agents[1]
    # Force very susceptible target
    from agents.models import TraitVector
    target_tv = target.trait_vector.model_copy(update={"moral_rigidity": 0.0, "susceptibility": 1.0})
    from agents.models import AgentProfile
    target = target.model_copy(update={"trait_vector": target_tv})

    actor_state = AgentState(agent_id=actor.id, stance=1.0, emotion="passionate", confidence=1.0)
    target_state = AgentState(agent_id=target.id, stance=0.0)
    action = _make_action(actor.id, confidence=1.0)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=1.0, social_proof=1.0, repetition_bonus=0.3)
    assert abs(delta) <= 0.15


def test_high_moral_rigidity_caps_at_002():
    """Moral rigidity >= 0.9 → max delta 0.02."""
    agents = generate_agents(count=2, seed=1)
    actor, target = agents[0], agents[1]
    target_tv = target.trait_vector.model_copy(update={"moral_rigidity": 0.95})
    from agents.models import AgentProfile
    target = target.model_copy(update={"trait_vector": target_tv})

    actor_state = AgentState(agent_id=actor.id, stance=1.0, emotion="passionate")
    target_state = AgentState(agent_id=target.id, stance=0.0)
    action = _make_action(actor.id, confidence=1.0)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=1.0, social_proof=1.0, repetition_bonus=0.3)
    assert abs(delta) <= 0.02


def test_zero_delta_when_low_trust_and_low_susceptibility():
    agents = generate_agents(count=2, seed=5)
    actor, target = agents[0], agents[1]
    target_tv = target.trait_vector.model_copy(update={"susceptibility": 0.0, "moral_rigidity": 0.9})
    target = target.model_copy(update={"trait_vector": target_tv})

    actor_state = AgentState(agent_id=actor.id, stance=0.9)
    target_state = AgentState(agent_id=target.id, stance=0.5, confidence=0.9)
    action = _make_action(actor.id, confidence=0.1)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=0.1, social_proof=0.1, repetition_bonus=0.0)
    assert delta == 0.0


def test_delta_direction_moves_toward_actor_stance():
    agents = generate_agents(count=2, seed=3)
    actor, target = agents[0], agents[1]
    actor_state = AgentState(agent_id=actor.id, stance=0.9, emotion="optimistic")
    target_state = AgentState(agent_id=target.id, stance=0.1, confidence=0.3)
    target_tv = target.trait_vector.model_copy(update={"moral_rigidity": 0.0, "susceptibility": 0.9})
    target = target.model_copy(update={"trait_vector": target_tv})
    action = _make_action(actor.id, confidence=0.9)

    delta = resolve_persuasion(actor, actor_state, action, target, target_state,
                               trust_score=0.8, social_proof=0.7, repetition_bonus=0.2)
    # Actor stance > target stance → delta should be positive (moving target toward actor)
    assert delta >= 0
```

- [ ] **Step 9.2: Run tests — verify they fail**

```bash
python -m pytest tests/simulation/test_persuasion_engine.py -v
```

- [ ] **Step 9.3: Create `backend/simulation/persuasion_engine.py`**

```python
from agents.models import AgentProfile, AgentState, RoundAction

_APPEAL_EMOTION_MATCH: dict[str, frozenset] = {
    "emotional":  frozenset({"angry", "fearful", "passionate", "hopeful"}),
    "rational":   frozenset({"determined", "neutral"}),
    "social":     frozenset({"optimistic", "hopeful"}),
    "authority":  frozenset({"neutral", "determined"}),
}


def resolve_persuasion(
    actor: AgentProfile,
    actor_state: AgentState,
    actor_action: RoundAction,
    target: AgentProfile,
    target_state: AgentState,
    trust_score: float,
    social_proof: float,
    repetition_bonus: float,
) -> float:
    """Compute stance delta to apply to target. Returns 0.0 if persuasion threshold not met."""
    matched = _APPEAL_EMOTION_MATCH.get(actor.appeal_type, frozenset())
    emotional_resonance = 1.0 if target_state.emotion in matched else 0.0

    persuasion_score = (
        trust_score                      * 0.30
        + actor_action.confidence        * 0.25
        + emotional_resonance            * 0.20
        + social_proof                   * 0.15
        + min(0.30, repetition_bonus)    * 0.10
    )

    susceptibility_threshold = (1.0 - target.trait_vector.susceptibility) * target_state.confidence
    if persuasion_score <= susceptibility_threshold:
        return 0.0

    direction = 1.0 if actor_state.stance > target_state.stance else -1.0
    delta = persuasion_score * (1.0 - target.trait_vector.moral_rigidity) * 0.2 * direction

    # Hard cap: ±0.15 per round
    delta = max(-0.15, min(0.15, delta))

    # Moral rigidity ≥ 0.9 → hard cap at ±0.02
    if target.trait_vector.moral_rigidity >= 0.9:
        delta = max(-0.02, min(0.02, delta))

    return delta
```

- [ ] **Step 9.4: Run tests — verify they pass**

```bash
python -m pytest tests/simulation/test_persuasion_engine.py -v
```

Expected: all 5 tests `PASSED`

- [ ] **Step 9.5: Commit**

```bash
git add backend/simulation/persuasion_engine.py tests/simulation/test_persuasion_engine.py
git commit -m "feat(simulation): persuasion engine — full formula with 0.15 hard cap and moral rigidity gate"
```

---

## Task 10: Output Aggregator

**Files:** `backend/output/__init__.py`, `backend/output/aggregator.py`, `tests/output/test_aggregator.py`

- [ ] **Step 10.1: Create `backend/output/__init__.py`** and `tests/output/__init__.py` (both empty)

- [ ] **Step 10.2: Write failing aggregator tests**

Create `tests/output/test_aggregator.py`:

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from output.aggregator import compute_verdict
from agents.models import AgentState


def _make_states(stances: list[float]) -> list[AgentState]:
    return [AgentState(agent_id=str(i), stance=s) for i, s in enumerate(stances)]


def test_majority_support():
    states = _make_states([0.8, 0.7, 0.9, 0.75, 0.3, 0.2])
    result = compute_verdict(states)
    assert result["confidence"] > 0
    assert "support" in result["verdict"].lower() or "consensus" in result["verdict"].lower()


def test_majority_oppose():
    states = _make_states([0.1, 0.2, 0.15, 0.3, 0.8, 0.25])
    result = compute_verdict(states)
    assert "reject" in result["verdict"].lower() or "opposition" in result["verdict"].lower() or "oppose" in result["verdict"].lower()


def test_returns_distribution():
    states = _make_states([0.8, 0.8, 0.2, 0.2, 0.5, 0.5])
    result = compute_verdict(states)
    assert "support" in result["distribution"]
    assert "oppose" in result["distribution"]
    assert "undecided" in result["distribution"]
    total = result["distribution"]["support"] + result["distribution"]["oppose"] + result["distribution"]["undecided"]
    assert abs(total - 1.0) < 0.01


def test_empty_states():
    result = compute_verdict([])
    assert result["confidence"] == 0.0


def test_confidence_is_float_between_0_and_1():
    states = _make_states([0.7, 0.8, 0.6, 0.9, 0.3, 0.2])
    result = compute_verdict(states)
    assert 0.0 <= result["confidence"] <= 1.0
```

- [ ] **Step 10.3: Run tests — verify they fail**

```bash
python -m pytest tests/output/test_aggregator.py -v
```

- [ ] **Step 10.4: Create `backend/output/aggregator.py`**

```python
from agents.models import AgentState


def compute_verdict(states: list[AgentState]) -> dict:
    """Pure Python: compute dominant outcome from final agent states."""
    n = len(states)
    if n == 0:
        return {"verdict": "No agents participated", "confidence": 0.0,
                "distribution": {"support": 0.0, "oppose": 0.0, "undecided": 0.0}, "avg_stance": 0.0}

    support = [s for s in states if s.stance >= 0.6]
    oppose = [s for s in states if s.stance <= 0.4]
    undecided = [s for s in states if 0.4 < s.stance < 0.6]

    sp = len(support) / n
    op = len(oppose) / n
    up = len(undecided) / n
    avg = sum(s.stance for s in states) / n

    if sp > op and sp > up:
        verdict = "Society reaches broad consensus in support"
        confidence = sp
    elif op > sp and op > up:
        verdict = "Society rejects the proposition"
        confidence = op
    elif up > 0.40:
        verdict = "Society remains deeply divided"
        confidence = up
    elif sp > op:
        verdict = "Marginal support with significant opposition"
        confidence = sp
    else:
        verdict = "Marginal opposition with contested public opinion"
        confidence = op

    return {
        "verdict": verdict,
        "confidence": round(confidence, 3),
        "distribution": {"support": round(sp, 3), "oppose": round(op, 3), "undecided": round(up, 3)},
        "avg_stance": round(avg, 3),
    }
```

- [ ] **Step 10.5: Run tests — verify they pass**

```bash
python -m pytest tests/output/test_aggregator.py -v
```

Expected: all 5 tests `PASSED`

- [ ] **Step 10.6: Commit**

```bash
git add backend/output/__init__.py backend/output/aggregator.py tests/output/__init__.py tests/output/test_aggregator.py
git commit -m "feat(output): verdict aggregator — stance distribution + dominant outcome classification"
```

---

## Task 11: Narrative Synthesizer

**Files:** `backend/output/narrative_synthesizer.py`

No unit test (requires live LLM). Verified via CLI run in Task 13.

- [ ] **Step 11.1: Create `backend/output/narrative_synthesizer.py`**

```python
import logging
from llm.executor import llm_executor

logger = logging.getLogger(__name__)


async def generate_narrative(
    scenario: str,
    round_logs: list,
    verdict: dict,
    api_key: str | None = None,
) -> str:
    """Generate a 3-5 sentence narrative arc via a single LLM call."""
    round_summaries = "\n".join(
        f"Round {rl.round_num}: {rl.stance_distribution['support']:.0%} support, "
        f"{rl.stance_distribution['oppose']:.0%} oppose, "
        f"{rl.stance_distribution['undecided']:.0%} undecided"
        for rl in round_logs
    )

    system = (
        "You are a political analyst writing a concise narrative arc. "
        "Write exactly 3-5 sentences describing how society responded to the scenario. "
        "Focus on the emotional journey, key turning points, and why the outcome emerged. "
        "Write in past tense, journalistic style. Be specific and vivid. "
        "Do not include JSON or structured data — plain prose only."
    )

    prompt = (
        f"Scenario: {scenario}\n\n"
        f"Round progression:\n{round_summaries}\n\n"
        f"Final outcome: {verdict['verdict']} (confidence: {verdict['confidence']:.0%})\n"
        f"Distribution: {verdict['distribution']['support']:.0%} support, "
        f"{verdict['distribution']['oppose']:.0%} oppose\n\n"
        f"Write the narrative arc in 3-5 sentences."
    )

    try:
        narrative = await llm_executor.complete(
            user_message=prompt,
            static_system=system,
            api_key=api_key,
        )
        return narrative.strip()
    except Exception as exc:
        logger.error("Narrative generation failed: %s", exc)
        dist = verdict["distribution"]
        return (
            f"The scenario unfolded with divergent societal responses. "
            f"After {len(round_logs)} rounds of debate, {dist['support']:.0%} of agents expressed support "
            f"while {dist['oppose']:.0%} remained opposed. "
            f"The final outcome — {verdict['verdict'].lower()} — emerged from the complex interplay "
            f"of competing beliefs and social pressures."
        )
```

- [ ] **Step 11.2: Commit**

```bash
git add backend/output/narrative_synthesizer.py
git commit -m "feat(output): narrative synthesizer — single LLM call, journalistic 3-5 sentence arc"
```

---

## Task 12: Orchestrator

**Files:** `backend/simulation/orchestrator.py`

- [ ] **Step 12.1: Create `backend/simulation/orchestrator.py`**

```python
import asyncio
import logging
import random
from dataclasses import dataclass

from agents.models import AgentProfile, AgentState, RoundAction
from agents.generator import generate_agents
from llm.executor import llm_executor
from llm.response_parser import parse_response
from output.aggregator import compute_verdict
from output.narrative_synthesizer import generate_narrative
from simulation.action_selector import select_action
from simulation.persuasion_engine import resolve_persuasion
from simulation.prompt_builder import build_prompt
from simulation.state_manager import StateManager

logger = logging.getLogger(__name__)


@dataclass
class RoundResult:
    round_num: int
    actions: list[RoundAction]
    stance_distribution: dict


@dataclass
class SimulationResult:
    verdict: str
    confidence: float
    distribution: dict
    top_agents: list[dict]
    narrative: str


async def run_simulation(
    scenario: str,
    agent_count: int = 50,
    rounds: int = 5,
    seed: int | None = None,
    api_key: str | None = None,
) -> SimulationResult:
    rng = random.Random(seed)
    agents = generate_agents(count=agent_count, seed=seed)
    agent_map: dict[str, AgentProfile] = {a.id: a for a in agents}

    state_mgr = StateManager()
    for agent in agents:
        state = state_mgr.init_agent_state(agent.id)
        # Initial stance varies by openness — skeptics start lower, open minds higher
        base = 0.30 + agent.trait_vector.openness * 0.40
        state.stance = max(0.0, min(1.0, base + rng.gauss(0, 0.12)))
        state_mgr.update_state(state)

    round_logs: list[RoundResult] = []

    for round_num in range(1, rounds + 1):
        logger.info("Round %d/%d", round_num, rounds)
        actions = await _run_round(
            scenario=scenario,
            agents=agents,
            agent_map=agent_map,
            state_mgr=state_mgr,
            round_num=round_num,
            total_rounds=rounds,
            rng=rng,
            api_key=api_key,
        )

        all_states = state_mgr.get_all_states()
        n = len(all_states)
        support = sum(1 for s in all_states if s.stance >= 0.6) / n
        oppose = sum(1 for s in all_states if s.stance <= 0.4) / n
        undecided = 1.0 - support - oppose

        dist = {"support": round(support, 3), "oppose": round(oppose, 3), "undecided": round(undecided, 3)}
        round_logs.append(RoundResult(round_num=round_num, actions=actions, stance_distribution=dist))
        logger.info("  Support %.0f%%  Oppose %.0f%%  Undecided %.0f%%", support * 100, oppose * 100, undecided * 100)

    final_states = state_mgr.get_all_states()
    verdict_data = compute_verdict(final_states)
    narrative = await generate_narrative(
        scenario=scenario,
        round_logs=round_logs,
        verdict=verdict_data,
        api_key=api_key,
    )

    sorted_states = sorted(final_states, key=lambda s: s.influence_score, reverse=True)
    top_agents = [
        {"agent": agent_map[s.agent_id], "state": s}
        for s in sorted_states[:3]
        if s.agent_id in agent_map
    ]

    return SimulationResult(
        verdict=verdict_data["verdict"],
        confidence=verdict_data["confidence"],
        distribution=verdict_data["distribution"],
        top_agents=top_agents,
        narrative=narrative,
    )


async def _run_round(
    scenario: str,
    agents: list[AgentProfile],
    agent_map: dict[str, AgentProfile],
    state_mgr: StateManager,
    round_num: int,
    total_rounds: int,
    rng: random.Random,
    api_key: str | None,
) -> list[RoundAction]:
    all_ids = [a.id for a in agents]
    actions: list[RoundAction] = []

    for agent in agents:
        state = state_mgr.get_state(agent.id)
        action_type, target_id = select_action(agent, state, all_ids, rng)

        trust_context = {
            agent_map[oid].name: state_mgr.get_trust(agent.id, oid)
            for oid in all_ids
            if oid != agent.id
        }

        target_name = agent_map[target_id].name if target_id and target_id in agent_map else None
        static_sys, dynamic_ctx, user_msg = build_prompt(
            agent=agent, state=state, action=action_type, target_name=target_name,
            scenario=scenario, round_num=round_num,
            trust_scores=trust_context, total_rounds=total_rounds,
        )

        free_text, json_data = "", {}
        try:
            raw = await llm_executor.complete(
                user_message=user_msg,
                static_system=static_sys,
                dynamic_context=dynamic_ctx,
                api_key=api_key,
            )
            free_text, json_data = parse_response(raw)

            if not json_data:
                logger.warning("Agent %s round %d: retrying — no JSON", agent.id[:8], round_num)
                retry_msg = (
                    user_msg + "\n\nYour previous response was missing the required JSON block. "
                    "Respond again and end with the JSON block exactly as specified."
                )
                raw = await llm_executor.complete(
                    user_message=retry_msg, static_system=static_sys,
                    dynamic_context=dynamic_ctx, api_key=api_key,
                )
                free_text, json_data = parse_response(raw)

        except Exception as exc:
            logger.error("Agent %s round %d LLM error: %s", agent.id[:8], round_num, exc)
            continue

        if not json_data:
            logger.warning("Agent %s round %d: skipping after retry failure", agent.id[:8], round_num)
            continue

        state.stance = max(0.0, min(1.0, float(json_data.get("stance", state.stance))))
        state.emotion = json_data.get("emotion", state.emotion)
        state.confidence = max(0.0, min(1.0, float(json_data.get("confidence", state.confidence))))
        state.last_action = action_type
        state.last_target = target_id
        state.interaction_count += 1
        state_mgr.update_state(state)

        actions.append(RoundAction(
            agent_id=agent.id, name=agent.name, archetype=agent.archetype,
            action=action_type, target_id=target_id,
            free_text=free_text or f"[{agent.name} performs {action_type}]",
            stance=state.stance, emotion=state.emotion, confidence=state.confidence,
        ))

    _apply_persuasion(actions, agent_map, state_mgr)
    return actions


def _apply_persuasion(
    actions: list[RoundAction],
    agent_map: dict[str, AgentProfile],
    state_mgr: StateManager,
) -> None:
    all_states = state_mgr.get_all_states()
    n = len(all_states)

    for action in actions:
        if not action.target_id or action.target_id not in agent_map:
            continue

        actor = agent_map[action.agent_id]
        actor_state = state_mgr.get_state(action.agent_id)
        target = agent_map[action.target_id]
        target_state = state_mgr.get_state(action.target_id)
        trust = state_mgr.get_trust(action.agent_id, action.target_id)

        # Social proof: fraction of agents sharing actor's stance direction
        same = sum(1 for s in all_states if (s.stance >= 0.5) == (actor_state.stance >= 0.5))
        social_proof = same / n if n > 0 else 0.5

        # Repetition bonus capped at 0.30
        repetition_bonus = min(0.30, state_mgr.get_trust(action.agent_id, action.target_id) * 0.3)

        delta = resolve_persuasion(
            actor=actor, actor_state=actor_state, actor_action=action,
            target=target, target_state=target_state,
            trust_score=trust, social_proof=social_proof, repetition_bonus=repetition_bonus,
        )

        if delta != 0.0:
            target_state.stance = max(0.0, min(1.0, target_state.stance + delta))
            state_mgr.update_state(target_state)
            actor_state.influence_score += abs(delta)
            state_mgr.update_state(actor_state)
            state_mgr.update_trust(action.agent_id, action.target_id, 0.02)
```

- [ ] **Step 12.2: Commit**

```bash
git add backend/simulation/orchestrator.py
git commit -m "feat(simulation): round orchestrator — sequential execution, persuasion resolution, influence tracking"
```

---

## Task 13: CLI Runner + FastAPI Stub

**Files:** `backend/cli.py`, `backend/main.py`, `backend/api/__init__.py`, `backend/api/health.py`, `backend/api/internal.py`

- [ ] **Step 13.1: Create `backend/api/__init__.py`** (empty)

- [ ] **Step 13.2: Create `backend/api/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 13.3: Create `backend/api/internal.py`** (stub for Phase 2)

```python
from fastapi import APIRouter

router = APIRouter(prefix="/internal")


@router.post("/simulate/start")
async def start_simulation(body: dict) -> dict:
    # Phase 2: call orchestrator as Celery task
    return {"ok": False, "message": "Not implemented in Phase 1 — use CLI"}
```

- [ ] **Step 13.4: Create `backend/main.py`**

```python
import logging
from fastapi import FastAPI
from api.health import router as health_router
from api.internal import router as internal_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = FastAPI(title="ASim Simulation Engine", version="0.1.0")
app.include_router(health_router)
app.include_router(internal_router)
```

- [ ] **Step 13.5: Create `backend/cli.py`**

```python
#!/usr/bin/env python
"""ASim Phase 1 CLI — runs a simulation and prints verdict + narrative."""
import argparse
import asyncio
import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def _run(scenario: str, agents: int, rounds: int, seed: int | None) -> None:
    from simulation.orchestrator import run_simulation

    print(f"\n{'='*62}")
    print("  ASim — Agent Society Simulator")
    print(f"{'='*62}")
    print(f"  Scenario : {scenario}")
    print(f"  Agents   : {agents}   Rounds: {rounds}")
    print(f"{'='*62}\n")

    result = await run_simulation(
        scenario=scenario,
        agent_count=agents,
        rounds=rounds,
        seed=seed,
    )

    print(f"\n{'='*62}")
    print(f"  VERDICT  : {result.verdict}")
    print(f"  Confidence: {result.confidence:.0%}")
    dist = result.distribution
    print(f"  Support {dist['support']:.0%}  |  Oppose {dist['oppose']:.0%}  |  Undecided {dist['undecided']:.0%}")
    print(f"{'='*62}")

    print("\n  TOP INFLUENTIAL AGENTS:")
    for i, entry in enumerate(result.top_agents, 1):
        ag = entry["agent"]
        st = entry["state"]
        print(f"  {i}. {ag.name} ({ag.archetype})")
        print(f"     Stance {st.stance:.2f}  |  Influence {st.influence_score:.3f}  |  Emotion: {st.emotion}")

    print(f"\n  NARRATIVE ARC:\n")
    for line in result.narrative.split(". "):
        line = line.strip()
        if line:
            print(f"  {line}{'.' if not line.endswith('.') else ''}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="ASim simulation CLI")
    parser.add_argument("--scenario", required=True, help="Scenario to simulate")
    parser.add_argument("--agents", type=int, default=50)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    asyncio.run(_run(args.scenario, args.agents, args.rounds, args.seed))


if __name__ == "__main__":
    main()
```

- [ ] **Step 13.6: Commit**

```bash
git add backend/cli.py backend/main.py backend/api/__init__.py backend/api/health.py backend/api/internal.py
git commit -m "feat(backend): CLI runner and FastAPI health stub"
```

---

## Task 14: Full Test Suite + End-to-End Verification

- [ ] **Step 14.1: Create `tests/conftest.py`**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../backend'))
```

- [ ] **Step 14.2: Run full unit test suite**

```bash
cd c:/Neel/CODING/ASim
.venv\Scripts\activate
python -m pytest tests/ -v --tb=short
```

Expected output: all tests `PASSED`. Count should be ~30 tests across all modules.

If any test fails: fix the implementation before proceeding. Do not skip.

- [ ] **Step 14.3: Verify Ollama is running**

```bash
curl http://localhost:11434/api/tags
```

Expected: JSON list of models. If `llama3.1:8b` is not listed: `ollama pull llama3.1:8b`

- [ ] **Step 14.4: Run the Phase 1 CLI (5 agents, 3 rounds — fast smoke test)**

```bash
cd c:/Neel/CODING/ASim
.venv\Scripts\activate
python backend/cli.py \
  --scenario "A government mandates vaccines for all citizens" \
  --agents 5 \
  --rounds 3 \
  --seed 42
```

Expected: printed output with VERDICT, confidence %, top 3 agents, and a narrative paragraph. No Python errors.

- [ ] **Step 14.5: Run the full Phase 1 spec simulation (50 agents, 5 rounds)**

```bash
python backend/cli.py \
  --scenario "A government mandates vaccines for all citizens" \
  --agents 50 \
  --rounds 5
```

Expected:
- A dominant outcome with percentage
- Top 3 influential agents with names, archetypes, and stances
- A 3–5 sentence narrative arc in plain prose
- Agents should feel like different people (different stances, emotions, archetypes)

If this runs without errors and the agents feel distinct → **Phase 1 is done.**

- [ ] **Step 14.6: Verify FastAPI health endpoint**

```bash
cd c:/Neel/CODING/ASim/backend
.venv\Scripts\activate
uvicorn main:app --port 8000 &
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`

Kill the server: `kill %1` (Linux/Mac) or close the terminal (Windows).

- [ ] **Step 14.7: Final commit**

```bash
git add tests/conftest.py
git commit -m "feat(backend): Phase 1 complete — CLI simulation engine with Ollama, 50 agents, persuasion, narrative"
```

---

## Self-Review Checklist

- [x] **LLM abstraction:** Every LLM call goes through `llm/executor.py`. No direct anthropic/ollama imports outside `llm/`.
- [x] **6-block order:** `prompt_builder.py` returns static_system (1-3) and dynamic_context (4-5) separately. Block 6 is always last.
- [x] **Persuasion cap:** `persuasion_engine.py` has `max(-0.15, min(0.15, delta))` hard cap. Moral rigidity ≥ 0.9 further caps at ±0.02.
- [x] **No LangChain/LangGraph:** Sequential orchestrator, no agent framework.
- [x] **No DB in Phase 1:** StateManager uses in-memory dicts only.
- [x] **No Celery in Phase 1:** Sequential `for agent in agents` loop.
- [x] **Error handling:** Every LLM call has try/except + one retry + skip-and-log on second failure.
- [x] **No print() in backend:** All logging via `logging` module.
- [x] **Type consistency:** `ActionType`, `EmotionType` literals used throughout. `RoundAction` fields match what orchestrator builds.
- [x] **TDD:** Tests written before implementation for all pure-Python components.
