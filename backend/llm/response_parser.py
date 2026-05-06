import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_response(text: str) -> tuple[str, dict]:
    """Extract free text and JSON block from LLM response.

    Returns (free_text, json_dict). json_dict is {} if no valid JSON found.
    """
    matches = list(re.finditer(r'\{[^{}]*\}', text, re.DOTALL))
    if not matches:
        logger.warning("No JSON block found in LLM response")
        return text.strip(), {}

    json_match = matches[-1]
    json_str = json_match.group(0)
    free_text = text[:json_match.start()].strip()

    try:
        return free_text, json.loads(json_str)
    except json.JSONDecodeError as exc:
        logger.warning("JSON parse error: %s. Raw: %.100s", exc, json_str)
        return free_text, {}
