import RPi.GPIO as GPIO
import time
from config import KEYPAD_ROWS, KEYPAD_COLS

KEYMAP = [
    ['1', '2', '3', 'A'],
    ['4', '5', '6', 'B'],
    ['7', '8', '9', 'C'],
    ['*', '0', '#', 'D'],
]

def setup():
    for pin in KEYPAD_ROWS:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
    for pin in KEYPAD_COLS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def read_key(timeout=5.0):
    """Block until a single key is pressed or timeout. Returns char or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        for r_idx, row_pin in enumerate(KEYPAD_ROWS):
            GPIO.output(row_pin, GPIO.HIGH)
            for c_idx, col_pin in enumerate(KEYPAD_COLS):
                if GPIO.input(col_pin) == GPIO.HIGH:
                    GPIO.output(row_pin, GPIO.LOW)
                    # Debounce: wait for release
                    while GPIO.input(col_pin) == GPIO.HIGH:
                        time.sleep(0.02)
                    return KEYMAP[r_idx][c_idx]
            GPIO.output(row_pin, GPIO.LOW)
        time.sleep(0.05)
    return None   # timeout
