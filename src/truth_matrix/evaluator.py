"""Deterministic evaluation of structured propositions over A–E."""

from __future__ import annotations

from typing import Any, Mapping

from truth_matrix.constants import SWITCHES

State = Mapping[str, bool]


def _count_on(state: State) -> int:
    return sum(1 for k in SWITCHES if state.get(k, False))


def evaluate_proposition(node: dict[str, Any], state: State) -> bool:
    """Recursively evaluate a proposition AST against switch states."""
    if not isinstance(node, dict) or "type" not in node:
        raise ValueError("Invalid proposition node")

    t = node["type"]
    if t == "switch_on":
        name = node["name"]
        if name not in SWITCHES:
            raise ValueError(f"Unknown switch: {name}")
        return bool(state.get(name, False))
    if t == "not":
        return not evaluate_proposition(node["child"], state)
    if t == "and":
        return all(evaluate_proposition(c, state) for c in node["children"])
    if t == "or":
        return any(evaluate_proposition(c, state) for c in node["children"])
    if t == "xor":
        return evaluate_proposition(node["left"], state) ^ evaluate_proposition(
            node["right"], state
        )
    if t == "implies":
        p = evaluate_proposition(node["antecedent"], state)
        q = evaluate_proposition(node["consequent"], state)
        return (not p) or q
    if t == "same":
        a, b = node["a"], node["b"]
        return bool(state.get(a, False)) == bool(state.get(b, False))
    if t == "count_eq":
        return _count_on(state) == int(node["value"])

    raise ValueError(f"Unknown proposition type: {t}")


def evaluate_puzzle(statements: dict[str, dict[str, Any]], state: State) -> bool:
    """
    True iff the puzzle is *consistent*: for each switch S, S is ON iff
    that switch's statement (about the world) holds.
    """
    for name in SWITCHES:
        if name not in statements:
            raise ValueError(f"Missing statement for {name}")
        prop_true = evaluate_proposition(statements[name], state)
        if state.get(name, False) != prop_true:
            return False
    return True


def proposition_satisfied(statements: dict[str, dict[str, Any]], state: State) -> dict[str, bool]:
    """Per-switch: does the physical position match the statement truth value?"""
    return {
        name: state.get(name, False) == evaluate_proposition(statements[name], state)
        for name in SWITCHES
    }
