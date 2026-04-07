import RPi.GPIO as GPIO
import time
from config import BUZZER_PIN, LED_GREEN_PIN, LED_RED_PIN

def setup():
    for pin in [BUZZER_PIN, LED_GREEN_PIN, LED_RED_PIN]:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

def _beep(pin, duration):
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(pin, GPIO.LOW)

def digit_ok():
    """Short confirmation blink/tone on correct digit."""
    GPIO.output(LED_GREEN_PIN, GPIO.HIGH)
    _beep(BUZZER_PIN, 0.05)
    GPIO.output(LED_GREEN_PIN, GPIO.LOW)

def wrong_code():
    """Error feedback: red LED + long buzz."""
    GPIO.output(LED_RED_PIN, GPIO.HIGH)
    _beep(BUZZER_PIN, 0.6)
    GPIO.output(LED_RED_PIN, GPIO.LOW)

def lockout(seconds):
    """Escalating buzz pattern during lockout."""
    print(f"[LOCKOUT] Locked for {seconds}s...")
    for _ in range(3):
        _beep(BUZZER_PIN, 0.2)
        time.sleep(0.1)
    time.sleep(seconds)

def success():
    """Green LED + victory tone."""
    GPIO.output(LED_GREEN_PIN, GPIO.HIGH)
    for _ in range(3):
        _beep(BUZZER_PIN, 0.1)
        time.sleep(0.05)
    # Leave green LED on until door fully opens
