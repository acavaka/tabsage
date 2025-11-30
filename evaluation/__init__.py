"""Evaluation framework for TabSage agents"""

from evaluation.runner import run_evaluations, load_test_config
from evaluation.regression import detect_regression, compare_results

__all__ = [
    "run_evaluations",
    "load_test_config",
    "detect_regression",
    "compare_results",
]

