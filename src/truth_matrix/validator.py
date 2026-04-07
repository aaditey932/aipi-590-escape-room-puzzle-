"""Brute-force validation: unique solution, schema checks."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from truth_matrix.constants import SWITCHES
from truth_matrix.evaluator import evaluate_puzzle

try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


@dataclass
class ValidationResult:
    ok: bool
    solution_count: int
    solutions: list[dict[str, bool]]
    error: str | None = None


def _all_assignments():
    """Yield all 2^5 switch assignments (deterministic order)."""
    for i in range(32):
        bits = [(i >> j) & 1 for j in range(5)]
        yield {SWITCHES[k]: bool(bits[k]) for k in range(5)}


def validate_puzzle_struct(
    puzzle: dict[str, Any],
    *,
    require_unique: bool = True,
) -> ValidationResult:
    """
    Enumerate all assignments; count how many satisfy evaluate_puzzle.
    If require_unique, ok iff exactly one solution exists.
    """
    try:
        statements = puzzle["statements"]
    except KeyError as e:
        return ValidationResult(False, 0, [], f"Missing statements: {e}")

    if set(statements.keys()) != set(SWITCHES):
        return ValidationResult(
            False,
            0,
            [],
            f"Statements must be exactly A–E, got {sorted(statements.keys())}",
        )

    solutions: list[dict[str, bool]] = []
    for state in _all_assignments():
        if evaluate_puzzle(statements, state):
            solutions.append(dict(state))

    n = len(solutions)
    if require_unique:
        ok = n == 1
        err = None if ok else (
            "No solution" if n == 0 else f"Multiple solutions ({n})"
        )
        return ValidationResult(ok, n, solutions, err)
    return ValidationResult(n > 0, n, solutions, None if n else "No solution")


def load_schema() -> dict[str, Any] | None:
    root = Path(__file__).resolve().parents[2]
    path = root / "schema" / "puzzle.schema.json"
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_puzzle_json(
    puzzle: dict[str, Any],
    *,
    use_json_schema: bool = True,
    require_unique: bool = True,
) -> ValidationResult:
    """JSON Schema (if available) + structural + unique-solution check."""
    if use_json_schema and jsonschema is not None:
        schema = load_schema()
        if schema is not None:
            try:
                jsonschema.validate(puzzle, schema)
            except jsonschema.ValidationError as e:
                return ValidationResult(False, 0, [], str(e.message))

    return validate_puzzle_struct(puzzle, require_unique=require_unique)


def load_puzzle_path(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    with p.open(encoding="utf-8") as f:
        return json.load(f)
