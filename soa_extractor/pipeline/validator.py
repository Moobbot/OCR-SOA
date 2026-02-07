import json
import re


def clean_json_block(text):
    """Extract JSON from markdown code blocks if present."""
    # Try to find ```json ... ```
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1)

    # Try to find ``` ... ```
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1)

    return text


def validate_json(raw_text, schema):
    """
    Parses and validates JSON against schema.
    Returns (data, error_message).
    """
    cleaned_text = clean_json_block(raw_text)

    try:
        data = json.loads(cleaned_text)
        # TODO: Add jsonschema validation if strict validation is needed
        # For now, just ensure it parses as JSON and is an object
        if not isinstance(data, dict):
            return None, "Output is not a JSON object"

        return data, None
    except json.JSONDecodeError as e:
        return None, f"JSON Decode Error: {str(e)}"
