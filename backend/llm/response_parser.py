import json
import logging

logger = logging.getLogger(__name__)


def _extract_json(text: str) -> tuple[dict | None, int, int]:
    """Find and parse the last valid JSON object in text.

    Returns (parsed_dict | None, start_index, end_index).
    start/end are -1 if no valid object found.
    """
    last_valid = None
    last_start = -1
    last_end = -1

    for i, ch in enumerate(text):
        if ch != '{':
            continue
        try:
            obj, end_offset = json.JSONDecoder().raw_decode(text, i)
            if isinstance(obj, dict):
                last_valid = obj
                last_start = i
                last_end = i + end_offset
        except json.JSONDecodeError:
            continue

    return last_valid, last_start, last_end


def parse_response(text: str) -> tuple[str, dict]:
    """Extract free text and JSON block from LLM response.

    Returns (free_text, json_dict). json_dict is {} if no valid JSON found.
    Handles nested JSON objects correctly via json.JSONDecoder scan.
    """
    obj, start, _end = _extract_json(text)
    if obj is not None:
        free_text = text[:start].strip()
        logger.debug("Parsed JSON from response: %s", str(obj)[:80])
        return free_text, obj

    logger.warning("No valid JSON found in response (len=%d)", len(text))
    return text.strip(), {}
