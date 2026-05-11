import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from agents.models import RoundAction
from output.hallucination_checker import check_hallucinations


def _action(agent_id: str, stance: float, target: str | None = None, free_text: str = "ok") -> RoundAction:
    return RoundAction(
        agent_id=agent_id, name=agent_id, archetype="Pragmatist",
        action="debate", target_id=target, free_text=free_text,
        stance=stance, emotion="neutral", confidence=0.5, argument_quality=0.5,
    )


class _RoundResult:
    def __init__(self, round_num: int, actions: list[RoundAction]):
        self.round_num = round_num
        self.actions = actions


def test_empty_logs_returns_green():
    res = check_hallucinations([], set())
    assert res["level"] == "green"
    assert res["total_warnings"] == 0
    assert res["total_actions"] == 0
    assert res["warning_rate"] == 0.0


def test_normal_play_stays_green():
    logs = [
        _RoundResult(1, [_action("a", 0.50), _action("b", 0.55)]),
        _RoundResult(2, [_action("a", 0.58), _action("b", 0.50)]),
    ]
    res = check_hallucinations(logs, {"a", "b"})
    assert res["level"] == "green"
    assert res["total_warnings"] == 0


def test_whiplash_detected():
    # Round 2 stance change exceeds WHIPLASH_DELTA (0.25)
    logs = [
        _RoundResult(1, [_action("a", 0.50)]),
        _RoundResult(2, [_action("a", 0.90)]),
    ]
    res = check_hallucinations(logs, {"a"})
    assert res["total_warnings"] >= 1
    assert any(d["type"] == "whiplash" for d in res["details"])


def test_empty_response_detected():
    logs = [_RoundResult(1, [_action("a", 0.5, free_text="   ")])]
    res = check_hallucinations(logs, {"a"})
    assert any(d["type"] == "empty_response" for d in res["details"])


def test_invalid_target_detected():
    logs = [_RoundResult(1, [_action("a", 0.5, target="ghost-42")])]
    res = check_hallucinations(logs, {"a"})
    assert any(d["type"] == "invalid_target" for d in res["details"])


def test_level_thresholds():
    # 100 actions, 20 warnings => 20% => red
    actions = [_action(f"a{i}", 0.5) for i in range(80)]
    actions += [_action(f"b{i}", 0.5, target="invalid") for i in range(20)]
    logs = [_RoundResult(1, actions)]
    valid = {a.agent_id for a in actions}
    res = check_hallucinations(logs, valid)
    assert res["warning_rate"] >= 0.15
    assert res["level"] == "red"


def test_details_capped():
    actions = [_action(f"a{i}", 0.5, target="ghost") for i in range(50)]
    logs = [_RoundResult(1, actions)]
    res = check_hallucinations(logs, {a.agent_id for a in actions})
    assert len(res["details"]) <= 20
    assert res["total_warnings"] == 50


def test_per_round_breakdown():
    logs = [
        _RoundResult(1, [_action("a", 0.5)]),
        _RoundResult(2, [_action("a", 0.5, target="ghost")]),
    ]
    res = check_hallucinations(logs, {"a"})
    assert len(res["per_round"]) == 2
    assert res["per_round"][0]["invalid_target"] == 0
    assert res["per_round"][1]["invalid_target"] == 1
