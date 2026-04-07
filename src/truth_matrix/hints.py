"""Template (and optional LLM) hints after repeated strikes."""

from __future__ import annotations

import logging
from typing import Any

from truth_matrix.constants import SWITCHES
from truth_matrix.evaluator import proposition_satisfied

log = logging.getLogger(__name__)


def hint_template(
    state: Any, current: dict[str, bool], solution: dict[str, bool]
) -> str:
    """Minimal deterministic hint: name a switch that differs from the unique solution."""
    wrong = [k for k in SWITCHES if current.get(k) != solution.get(k)]
    if not wrong:
        return "All switches match the solution (try Confirm again)."
    k = wrong[0]
    want = solution[k]
    return (
        f"Try setting switch {k} to {'ON' if want else 'OFF'} "
        f"({sum(1 for _ in wrong)} position(s) differ from a consistent state)."
    )


def hint_after_strikes(
    state: Any,
    current: dict[str, bool],
    *,
    solution: dict[str, bool] | None = None,
    use_llm: bool = False,
) -> str | None:
    from truth_matrix.validator import validate_puzzle_json

    if state.strikes < state.hint_strike_threshold:
        return None
    p = state.puzzle
    vr = validate_puzzle_json(p, require_unique=True)
    if not vr.ok or not vr.solutions:
        return "Puzzle has no unique solution in the validator; check JSON."
    sol = solution or vr.solutions[0]
    if use_llm:
        try:
            from truth_matrix.llm_author import hint_llm

            text = hint_llm(p, current, sol)
            if text:
                return text
        except Exception as e:  # pragma: no cover
            log.debug("LLM hint failed: %s", e)
    return hint_template(state, current, sol)


def diagnostic_summary(puzzle: dict[str, Any], switches: dict[str, bool]) -> str:
    """Describe which switch statements fail (for debugging / rich hints)."""
    stmts = puzzle["statements"]
    sat = proposition_satisfied(stmts, switches)
    bad = [k for k, ok in sat.items() if not ok]
    if not bad:
        return "All statements match switch positions (global consistency may still fail)."
    return "Statements inconsistent for: " + ", ".join(bad)
