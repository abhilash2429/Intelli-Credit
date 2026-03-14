"""
Shared formatting helpers for financial displays.
"""

from __future__ import annotations

from typing import Any


def format_ratio(value: Any, decimals: int = 2, suffix: str = "x") -> str:
    """Format financial ratios cleanly."""
    if value is None:
        return "Not Available"
    if isinstance(value, float) and value != value:  # NaN check
        return "Not Available"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "Not Available"
    return f"{round(numeric, decimals)}{suffix}"


def format_currency_cr(value: Any) -> str:
    """Format currency in Crores."""
    if value is None:
        return "Not Available"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "Not Available"
    return f"\u20b9{round(numeric, 2):,.2f} Cr"


def format_percentage(value: Any) -> str:
    """Format percentage values."""
    if value is None:
        return "Not Available"
    if isinstance(value, float) and value != value:  # NaN check
        return "Not Available"
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "Not Available"
    return f"{round(numeric, 1)}%"
