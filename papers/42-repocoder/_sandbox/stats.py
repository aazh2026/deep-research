"""Statistical helpers."""
from typing import List, Optional

def median(values: List[float]) -> Optional[float]:
    """Return the median of values, or None if empty."""
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n % 2 == 0:
        return (s[n//2 - 1] + s[n//2]) / 2
    return s[n//2]

def variance(values: List[float]) -> Optional[float]:
    """Return sample variance, or None if fewer than 2 values."""
    if len(values) < 2:
        return None
    m = sum(values) / len(values)
    return sum((v - m) ** 2 for v in values) / (len(values) - 1)

def safe_max(values: List[float]) -> Optional[float]:
    """Return max, or None if empty."""
    if not values:
        return None
    return max(values)
