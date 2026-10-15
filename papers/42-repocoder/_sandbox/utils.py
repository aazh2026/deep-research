"""Utility helpers for the calculator app."""
from typing import List, Optional

def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b

def subtract(a: float, b: float) -> float:
    """Return a - b."""
    return a - b

def multiply(a: float, b: float) -> float:
    """Return a * b."""
    return a * b

def divide(a: float, b: float) -> Optional[float]:
    """Return a / b, or None if b is zero."""
    if b == 0:
        return None
    return a / b

def sum_list(values: List[float]) -> float:
    """Return sum of values, defaulting to 0 for empty list."""
    if not values:
        return 0.0
    return sum(values)

def average(values: List[float]) -> Optional[float]:
    """Return mean of values, or None if empty."""
    if not values:
        return None
    return sum(values) / len(values)
