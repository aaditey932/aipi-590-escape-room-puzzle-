"""Truth Matrix: boolean switch puzzle core and Raspberry Pi runtime."""

from truth_matrix.evaluator import evaluate_proposition, evaluate_puzzle
from truth_matrix.validator import ValidationResult, validate_puzzle_json

__all__ = [
    "evaluate_proposition",
    "evaluate_puzzle",
    "validate_puzzle_json",
    "ValidationResult",
]
