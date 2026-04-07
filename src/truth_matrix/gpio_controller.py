"""GPIO abstraction: real gpiozero on Raspberry Pi, mock elsewhere."""

from __future__ import annotations

import logging
import time
from typing import Protocol

from truth_matrix.config import PinConfig, load_pin_config
from truth_matrix.constants import SWITCHES

log = logging.getLogger(__name__)


class GPIOBackend(Protocol):
    def read_switch_states(self) -> dict[str, bool]:
        """True = switch ON (player considers statement true)."""

    def read_confirm_pressed(self) -> bool:
        """True while confirm button is held (edge handled by caller)."""

    def set_leds(self, green: bool, red: bool) -> None:
        ...

    def sensors_armed(self) -> bool:
        """True if optional gate sensors allow play."""

    def close(self) -> None:
        ...


class MockGPIO(GPIOBackend):
    """Keyboard-driven mock for development (set TRUTH_MATRIX_MOCK_GPIO=1)."""

    def __init__(self, cfg: PinConfig) -> None:
        self._cfg = cfg
        self._switches = {k: False for k in SWITCHES}
        self._green = False
        self._red = False
        self._tilt = True
        self._reed = True

    def read_switch_states(self) -> dict[str, bool]:
        return dict(self._switches)

    def read_confirm_pressed(self) -> bool:
        return False

    def set_leds(self, green: bool, red: bool) -> None:
        self._green = green
        self._red = red
        log.debug("LED green=%s red=%s", green, red)

    def sensors_armed(self) -> bool:
        if self._cfg.tilt is None and self._cfg.reed is None:
            return True
        ok = True
        if self._cfg.tilt is not None:
            ok = ok and self._tilt
        if self._cfg.reed is not None:
            ok = ok and self._reed
        return ok

    def close(self) -> None:
        pass

    # --- test helpers ---
    def mock_set_switch(self, name: str, on: bool) -> None:
        self._switches[name] = on

    def mock_set_sensors(self, *, tilt: bool | None = None, reed: bool | None = None) -> None:
        if tilt is not None:
            self._tilt = tilt
        if reed is not None:
            self._reed = reed


class PiGPIO(GPIOBackend):
    def __init__(self, cfg: PinConfig) -> None:
        from gpiozero import Button, LED  # type: ignore import-not-found

        self._cfg = cfg
        self._buttons: dict[str, Button] = {}
        for name, pin in cfg.switches.items():
            b = Button(pin, pull_up=True, bounce_time=0.05)
            self._buttons[name] = b
        self._confirm = Button(cfg.confirm, pull_up=True, bounce_time=0.08)
        self._led_g = LED(cfg.led_green)
        self._led_r = LED(cfg.led_red)
        self._tilt_btn = Button(cfg.tilt, pull_up=True) if cfg.tilt is not None else None
        self._reed_btn = Button(cfg.reed, pull_up=True) if cfg.reed is not None else None

    def read_switch_states(self) -> dict[str, bool]:
        out: dict[str, bool] = {}
        for name, btn in self._buttons.items():
            pressed = btn.is_pressed
            # Default wiring: pull-up, switch to GND when ON -> is_pressed means ON.
            out[name] = (not pressed) if self._cfg.active_high_switches else pressed
        return out

    def read_confirm_pressed(self) -> bool:
        return self._confirm.is_pressed

    def set_leds(self, green: bool, red: bool) -> None:
        self._led_g.value = 1 if green else 0
        self._led_r.value = 1 if red else 0

    def sensors_armed(self) -> bool:
        if self._tilt_btn is None and self._reed_btn is None:
            return True
        ok = True
        if self._tilt_btn is not None:
            ok = ok and self._tilt_btn.is_pressed
        if self._reed_btn is not None:
            ok = ok and self._reed_btn.is_pressed
        return ok

    def close(self) -> None:
        for b in self._buttons.values():
            b.close()
        self._confirm.close()
        self._led_g.close()
        self._led_r.close()
        if self._tilt_btn:
            self._tilt_btn.close()
        if self._reed_btn:
            self._reed_btn.close()


def create_gpio(cfg: PinConfig | None = None) -> GPIOBackend:
    cfg = cfg or load_pin_config()
    if cfg.mock_gpio:
        log.info("Using mock GPIO")
        return MockGPIO(cfg)
    try:
        return PiGPIO(cfg)
    except Exception as e:  # pragma: no cover
        log.warning("GPIO init failed (%s); falling back to mock", e)
        return MockGPIO(cfg)


def debounced_confirm(
    backend: GPIOBackend,
    *,
    hold_seconds: float = 0.05,
    samples: int = 3,
) -> bool:
    """True if confirm appears stable pressed."""
    if not backend.read_confirm_pressed():
        return False
    time.sleep(hold_seconds)
    return all(backend.read_confirm_pressed() for _ in range(samples))
