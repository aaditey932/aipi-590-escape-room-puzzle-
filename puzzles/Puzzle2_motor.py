import RPi.GPIO as GPIO
import time
from config import MOTOR_PIN, DOOR_OPEN_DUTY, DOOR_CLOSED_DUTY

_pwm = None

def setup():
    global _pwm
    GPIO.setup(MOTOR_PIN, GPIO.OUT)
    _pwm = GPIO.PWM(MOTOR_PIN, 50)   # 50 Hz for servo
    _pwm.start(DOOR_CLOSED_DUTY)
    time.sleep(0.5)

def open_door():
    print("[MOTOR] Opening door...")
    _pwm.ChangeDutyCycle(DOOR_OPEN_DUTY)
    time.sleep(1.0)
    _pwm.ChangeDutyCycle(0)           # Stop jitter

def close_door():
    _pwm.ChangeDutyCycle(DOOR_CLOSED_DUTY)
    time.sleep(1.0)
    _pwm.ChangeDutyCycle(0)

def cleanup():
    _pwm.stop()
