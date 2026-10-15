"""Calculator app — uses utils and stats helpers."""
from utils import add, subtract, divide, sum_list, average
from stats import median, variance, safe_max

def basic_calc(a: float, b: float) -> dict:
    """Return a dict with sum, diff, and ratio of a and b."""
    return {
        "sum": __HOLE_SUM__,
        "diff": __HOLE_DIFF__,
        "ratio": __HOLE_RATIO__,
    }

def list_stats(values):
    """Return descriptive stats for a numeric list."""
    return {
        "n": __HOLE_N__,
        "sum": __HOLE_SUM_LIST__,
        "avg": __HOLE_AVG__,
        "med": __HOLE_MED__,
        "var": __HOLE_VAR__,
        "mx": __HOLE_MAX__,
    }
