"""CLI: python -m truth_matrix [validate|generate|play] ..."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(description="Truth Matrix puzzle tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("validate", help="Validate a puzzle JSON file")
    v.add_argument("path", type=Path, help="Path to puzzle.json")

    g = sub.add_parser("generate", help="Generate an approved puzzle (template or LLM)")
    g.add_argument("--out", type=Path, default=Path("puzzles/generated.json"))
    g.add_argument("--difficulty", type=int, default=2)
    g.add_argument(
        "--backend",
        choices=("template", "openai", "ollama"),
        default=os.environ.get("TRUTH_MATRIX_LLM_BACKEND", "template"),
    )

    pl = sub.add_parser("play", help="Run interactive loop on Raspberry Pi (or mock)")
    pl.add_argument("--puzzle", type=Path, default=Path("puzzles/example_plan.json"))
    pl.add_argument("--mock", action="store_true", help="Force mock GPIO")

    args = p.parse_args(argv)

    if args.cmd == "validate":
        from truth_matrix.validator import load_puzzle_path, validate_puzzle_json

        puzzle = load_puzzle_path(args.path)
        r = validate_puzzle_json(puzzle)
        print(json.dumps({"ok": r.ok, "solutions": len(r.solutions), "error": r.error}, indent=2))
        return 0 if r.ok else 1

    if args.cmd == "generate":
        from truth_matrix.llm_author import generate_validated_puzzle, save_puzzle

        puzzle, err = generate_validated_puzzle(difficulty=args.difficulty, backend=args.backend)
        if not puzzle:
            log.error("Generation failed: %s", err)
            return 1
        save_puzzle(puzzle, args.out)
        log.info("Wrote %s", args.out)
        return 0

    if args.cmd == "play":
        if args.mock:
            os.environ["TRUTH_MATRIX_MOCK_GPIO"] = "1"
        from truth_matrix.display import try_create_display
        from truth_matrix.game import run_interactive

        display = None
        if os.environ.get("TRUTH_MATRIX_USE_OLED"):
            display = try_create_display()
        run_interactive(args.puzzle, display=display)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
