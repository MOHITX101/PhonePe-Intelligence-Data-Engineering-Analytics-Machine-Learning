import math
from typing import Optional


def format_compact_number(
    value: Optional[float],
    decimals: int = 2,
) -> str:
    """
    Convert large numbers into readable dashboard labels.
    """

    if value is None:
        return "—"

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return "—"

    if math.isnan(numeric_value):
        return "—"

    absolute_value = abs(numeric_value)

    if absolute_value >= 1_000_000_000_000:
        return (
            f"{numeric_value / 1_000_000_000_000:.{decimals}f}T"
        )

    if absolute_value >= 1_000_000_000:
        return (
            f"{numeric_value / 1_000_000_000:.{decimals}f}B"
        )

    if absolute_value >= 1_000_000:
        return (
            f"{numeric_value / 1_000_000:.{decimals}f}M"
        )

    if absolute_value >= 1_000:
        return (
            f"{numeric_value / 1_000:.{decimals}f}K"
        )

    return f"{numeric_value:,.{decimals}f}"


def format_percentage(
    value: Optional[float],
    decimals: int = 2,
) -> str:
    if value is None:
        return "—"

    try:
        return f"{float(value):.{decimals}f}%"
    except (TypeError, ValueError):
        return "—"


def format_state_name(state_slug: str) -> str:
    if not state_slug:
        return "Unknown"

    return (
        state_slug
        .replace("-&-", " & ")
        .replace("-", " ")
        .title()
    )