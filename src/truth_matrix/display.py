"""Optional SSD1306 OLED via luma.oled (I2C)."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def try_create_display() -> Any | None:
    """Return a Display object or None if hardware/library unavailable."""
    try:
        from luma.core.interface.serial import i2c  # type: ignore
        from luma.oled.device import ssd1306  # type: ignore
    except ImportError:
        log.info("luma.oled not installed; running without OLED")
        return None
    try:
        serial = i2c(port=1, address=0x3C)
        device = ssd1306(serial)
    except Exception as e:  # pragma: no cover
        log.warning("OLED init failed: %s", e)
        return None
    return OLEDDisplay(device)


class OLEDDisplay:
    def __init__(self, device: Any) -> None:
        self._device = device
        from PIL import Image, ImageDraw, ImageFont  # type: ignore

        self._Image = Image
        self._ImageDraw = ImageDraw
        self._ImageFont = ImageFont
        self._font = ImageFont.load_default()

    def _draw_lines(self, lines: list[str]) -> None:
        img = self._Image.new(self._device.mode, self._device.size)
        draw = self._ImageDraw.Draw(img)
        y = 0
        for line in lines[:8]:
            draw.text((0, y), line[:26], font=self._font, fill="white")
            y += 10
        self._device.display(img)

    def render_idle(self, state: Any) -> None:
        p = state.puzzle
        lines = [p.get("title", p.get("id", "Truth Matrix"))]
        disp = p.get("display", {})
        for k in ("A", "B", "C", "D", "E"):
            if k in disp:
                lines.append(f"{k}: {disp[k]}")
        self._draw_lines(lines)

    def show_success(self) -> None:
        self._draw_lines(["DEFUSED", "Nice work."])

    def show_hint(self, text: str) -> None:
        words = text.split()
        lines: list[str] = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + 1 > 21:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + " " + w).strip()
        if cur:
            lines.append(cur)
        self._draw_lines(["Hint:"] + lines[:6])
