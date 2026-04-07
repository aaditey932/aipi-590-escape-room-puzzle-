"""Runtime game loop: strikes, hints tier, GPIO, optional display."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from truth_matrix.config import load_pin_config
from truth_matrix.constants import SWITCHES
from truth_matrix.evaluator import evaluate_puzzle
from truth_matrix.gpio_controller import GPIOBackend, create_gpio, debounced_confirm
from truth_matrix.hints import hint_after_strikes
from truth_matrix.validator import load_puzzle_path

log = logging.getLogger(__name__)


@dataclass
class GameState:
    puzzle: dict[str, Any]
    strikes: int = 0
    solved: bool = False
    max_strikes: int = 5
    hint_strike_threshold: int = 2

    def on_wrong(self) -> None:
        self.strikes += 1

    def can_continue(self) -> bool:
        return not self.solved and self.strikes < self.max_strikes


def run_round(
    state: GameState,
    switches: dict[str, bool],
    *,
    hint_fn: Callable[[GameState, dict[str, bool]], str | None] | None = None,
) -> tuple[bool, str | None]:
    """
    Evaluate current switch snapshot. Returns (success, optional hint text).
    """
    stmts = state.puzzle["statements"]
    ok = evaluate_puzzle(stmts, switches)
    if ok:
        state.solved = True
        return True, None
    state.on_wrong()
    hint = None
    if hint_fn and state.strikes >= state.hint_strike_threshold:
        hint = hint_fn(state, switches)
    return False, hint


def run_interactive(
    puzzle_path: str | Path,
    *,
    gpio: GPIOBackend | None = None,
    display: Any = None,
) -> None:
    """Blocking loop: poll confirm, evaluate, drive LEDs (and optional OLED)."""
    puzzle = load_puzzle_path(puzzle_path)
    state = GameState(puzzle=puzzle)
    cfg = load_pin_config()
    backend = gpio or create_gpio(cfg)
    display_mod = display

    prev_confirm = False
    try:
        while state.can_continue():
            if display_mod and hasattr(display_mod, "render_idle"):
                display_mod.render_idle(state)

            pressed = backend.read_confirm_pressed()
            edge = pressed and not prev_confirm
            prev_confirm = pressed

            if edge and debounced_confirm(backend):
                if not backend.sensors_armed():
                    backend.set_leds(False, True)
                    time.sleep(0.2)
                    backend.set_leds(False, False)
                    log.warning("Sensors not armed")
                    continue

                switches = backend.read_switch_states()
                def _hint(s: GameState, sw: dict[str, bool]) -> str | None:
                    return hint_after_strikes(s, sw, use_llm=False)

                success, hint = run_round(state, switches, hint_fn=_hint)
                if success:
                    backend.set_leds(True, False)
                    if display_mod and hasattr(display_mod, "show_success"):
                        display_mod.show_success()
                    log.info("Defused!")
                    break
                backend.set_leds(False, True)
                time.sleep(0.3)
                backend.set_leds(False, False)
                if hint and display_mod and hasattr(display_mod, "show_hint"):
                    display_mod.show_hint(hint)
                elif hint:
                    log.info("Hint: %s", hint)

            time.sleep(0.02)
    finally:
        backend.close()


def run_mock_demo(puzzle_path: str | Path) -> GameState:
    """Drive a full success path with mock GPIO (for tests)."""
    puzzle = load_puzzle_path(puzzle_path)
    from truth_matrix.validator import validate_puzzle_json

    vr = validate_puzzle_json(puzzle)
    if not vr.ok:
        raise ValueError(vr.error or "Invalid puzzle")
    solution = vr.solutions[0]

    cfg = load_pin_config(mock_override=True)
    from truth_matrix.gpio_controller import MockGPIO

    backend = MockGPIO(cfg)
    state = GameState(puzzle=puzzle)
    for k, v in solution.items():
        backend.mock_set_switch(k, v)
    success, _ = run_round(state, backend.read_switch_states())
    assert success
    return state
