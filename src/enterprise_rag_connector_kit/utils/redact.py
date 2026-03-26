from __future__ import annotations


def mask_secret(value: str | None, *, prefix: int = 4, suffix: int = 4) -> str:
    """
    Safely mask a secret for logging output.

    This function preserves a configurable prefix and suffix of the input
    while masking the middle portion. If the value is too short or invalid,
    a fully masked placeholder is returned.

    Examples:
        ``abcdefghijkl`` -> ``abcd...ijkl``
        ``short`` -> ``****``
        ``None`` -> ``****``

    Args:
        value: The input string containing sensitive data.
        prefix: Number of characters to preserve at the beginning.
        suffix: Number of characters to preserve at the end.

    Returns:
        A masked string safe for logging.
    """
    if value is None:
        return "****"

    trimmed = value.strip()
    if not trimmed:
        return "****"

    if len(trimmed) <= prefix + suffix:
        return "****"

    return f"{trimmed[:prefix]}...{trimmed[-suffix:]}"