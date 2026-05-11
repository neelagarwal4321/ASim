import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from agents.models import AgentState, RoundAction
from memory.compressor import update_memory, MAX_RECENT, SEP


def _action(agent_id: str = "a", action: str = "debate", target: str | None = None,
            stance: float = 0.5, emotion: str = "neutral") -> RoundAction:
    return RoundAction(
        agent_id=agent_id, name=agent_id, archetype="Pragmatist",
        action=action, target_id=target, free_text="hi",
        stance=stance, emotion=emotion, confidence=0.5, argument_quality=0.5,
    )


def _state(memory: str = "") -> AgentState:
    return AgentState(agent_id="a", memory_text=memory)


def test_first_entry_seeds_memory():
    new = update_memory(_state(), _action(), {"support": 0.5, "oppose": 0.3, "undecided": 0.2}, round_num=1)
    assert new.startswith("R1:debate")
    assert "stance=0.50" in new
    assert "crowd=support50%" in new


def test_short_memory_appends_without_compressing():
    state = _state()
    for i in range(1, MAX_RECENT + 1):
        state.memory_text = update_memory(state, _action(stance=0.5 + i * 0.05),
                                          {"support": 0.5, "oppose": 0.3, "undecided": 0.2},
                                          round_num=i)
    entries = state.memory_text.split(SEP)
    assert len(entries) == MAX_RECENT
    assert all(e.startswith(f"R{i + 1}:") for i, e in enumerate(entries))


def test_overflow_compresses_into_sum_tag():
    state = _state()
    for i in range(1, MAX_RECENT + 3):
        state.memory_text = update_memory(state, _action(stance=0.5 + i * 0.02),
                                          {"support": 0.5, "oppose": 0.3, "undecided": 0.2},
                                          round_num=i)
    entries = state.memory_text.split(SEP)
    assert len(entries) == MAX_RECENT + 1
    assert entries[0].startswith("SUM(")
    assert entries[0].endswith(")")


def test_sum_tag_increments_rather_than_nesting():
    state = _state()
    for i in range(1, 10):
        state.memory_text = update_memory(state, _action(),
                                          {"support": 0.5, "oppose": 0.3, "undecided": 0.2},
                                          round_num=i)
    entries = state.memory_text.split(SEP)
    # Only one SUM tag, never SUM containing SUM.
    assert entries.count(entries[0]) == 1
    assert entries[0].startswith("SUM(")
    # 9 total rounds, MAX_RECENT (=3) kept verbatim, 6 compressed
    assert entries[0] == f"SUM({9 - MAX_RECENT})"


def test_distribution_missing_does_not_crash():
    new = update_memory(_state(), _action(), {}, round_num=1)
    assert "crowd=" not in new
    assert new.startswith("R1:debate")
