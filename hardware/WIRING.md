# Truth Matrix — Raspberry Pi wiring

Use **3.3 V logic** on GPIO. Common ground (GND) for all components.

## Default BCM pin map

Configurable via environment variables (see `src/truth_matrix/config.py`). Defaults:

| Signal   | BCM GPIO | Notes                          |
|----------|----------|--------------------------------|
| Switch A | 17       | INPUT, internal pull-up, LOW=ON |
| Switch B | 27       | same                           |
| Switch C | 22       | same                           |
| Switch D | 23       | same                           |
| Switch E | 24       | same                           |
| Confirm  | 25       | INPUT, pull-up, LOW when pressed |
| LED green| 5        | OUTPUT                         |
| LED red  | 6        | OUTPUT                         |
| OLED SDA | 2 (SDA)  | I2C1 — SSD1306 128×64          |
| OLED SCL | 3 (SCL)  | I2C1                           |
| Tilt     | 16       | Optional; HIGH = armed         |
| Reed     | 26       | Optional; HIGH = armed         |

Tie each toggle between **GPIO and GND** so the pin reads LOW when ON (closed to ground) with pull-up enabled. If your switches are wired the other way, set `TRUTH_MATRIX_ACTIVE_HIGH=1` in the environment.

## LEDs

Use a current-limiting resistor in series (e.g. 330 Ω) for each LED.

## Optional I2C OLED

Enable I2C with `sudo raspi-config` → Interface Options → I2C. Install Python deps from project `requirements.txt` (`luma.oled`).

## Optional sensors

- **Tilt ball switch:** one terminal to GPIO, one to GND; INPUT with pull-up, contact closed when flat (depends on part — verify with a multimeter).
- **Reed switch:** magnet present closes contact; wire same as a momentary switch.

When optional sensors are enabled in config, both must read **armed** (per pin polarity) before Confirm is accepted.
