from typing import Any


def _coerce(raw_value: str) -> bool | int | str:
    """Coerce a raw string value.

    'true'/'false' (case-insensitive) -> bool; otherwise try int();
    otherwise return the string unchanged.
    """
    lowered = raw_value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(raw_value)
    except ValueError:
        return raw_value


def _parse_line(raw_line: str) -> tuple[str, Any] | None:
    """Parse a single line into (key, value), or None if it is skipped.

    Quirk preserved: only the segment between the first and second '='
    is used as the value.
    """
    line = raw_line.strip()
    if line == "" or line[0] == "#":
        return None
    parts = line.split("=")
    if len(parts) < 2:
        return None
    key = parts[0].strip()
    raw_value = parts[1].strip()
    return key, _coerce(raw_value)


def parse(text: str, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    """Parse key=value config text into a new dict.

    Starts from a shallow copy of `defaults`; later keys override earlier ones.
    """
    result: dict[str, Any] = dict(defaults) if defaults else {}
    for raw_line in text.split("\n"):
        parsed = _parse_line(raw_line)
        if parsed is None:
            continue
        key, value = parsed
        result[key] = value
    return result
