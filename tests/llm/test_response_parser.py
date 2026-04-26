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
