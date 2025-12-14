from __future__ import annotations

import re
from typing import Any


TEMPLATE_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_\-\.]+)\s*}}")


def resolve_templates(value: Any, context: dict[str, Any]) -> Any:
    """Recursively resolve template strings in configs using parent outputs/params."""
    if isinstance(value, dict):
        return {k: resolve_templates(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_templates(item, context) for item in value]
    if isinstance(value, str):
        trimmed = value.strip()
        full_match = TEMPLATE_PATTERN.fullmatch(trimmed)
        if full_match:
            match_key = full_match.group(1)
            replacement = _lookup_template(match_key, context)
            if replacement is None:
                raise ValueError(f"Missing data for template {match_key}")
            return replacement

        def replacer(match: re.Match[str]) -> str:
            match_key = match.group(1)
            replacement = _lookup_template(match_key, context)
            if replacement is None:
                raise ValueError(f"Missing data for template {match_key}")
            return str(replacement)

        return TEMPLATE_PATTERN.sub(replacer, value)
    return value


def _lookup_template(key: str, context: dict[str, Any]) -> Any:
    parts = key.split(".")
    root = parts[0]
    cursor: Any = context.get(root)
    for part in parts[1:]:
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        else:
            return None
    return cursor
