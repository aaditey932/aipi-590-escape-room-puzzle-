"""Environment-driven pin map and feature flags."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    if v is None or v.strip() == "":
        return default
    return int(v)


def _env_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class PinConfig:
    switches: dict[str, int]
    confirm: int
    led_green: int
    led_red: int
    tilt: int | None
    reed: int | None
    """If set, both tilt and reed must read armed for Confirm to be accepted."""

    active_high_switches: bool
    """If True, switch closed = HIGH. Default False: pull-up, closed to GND = LOW = ON."""

    mock_gpio: bool


def load_pin_config(mock_override: bool | None = None) -> PinConfig:
    mock = (
        mock_override
        if mock_override is not None
        else _env_bool("TRUTH_MATRIX_MOCK_GPIO", False)
    )
    return PinConfig(
        switches={
            "A": _env_int("TRUTH_MATRIX_PIN_A", 17),
            "B": _env_int("TRUTH_MATRIX_PIN_B", 27),
            "C": _env_int("TRUTH_MATRIX_PIN_C", 22),
            "D": _env_int("TRUTH_MATRIX_PIN_D", 23),
            "E": _env_int("TRUTH_MATRIX_PIN_E", 24),
        },
        confirm=_env_int("TRUTH_MATRIX_PIN_CONFIRM", 25),
        led_green=_env_int("TRUTH_MATRIX_PIN_LED_GREEN", 5),
        led_red=_env_int("TRUTH_MATRIX_PIN_LED_RED", 6),
        tilt=_env_int("TRUTH_MATRIX_PIN_TILT", 16) if _env_bool("TRUTH_MATRIX_USE_TILT", False) else None,
        reed=_env_int("TRUTH_MATRIX_PIN_REED", 26) if _env_bool("TRUTH_MATRIX_USE_REED", False) else None,
        active_high_switches=_env_bool("TRUTH_MATRIX_ACTIVE_HIGH", False),
        mock_gpio=mock,
    )
