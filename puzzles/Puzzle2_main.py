import RPi.GPIO as GPIO
import keypad, feedback, motor
from game import run

if __name__ == "__main__":
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    try:
        keypad.setup()
        feedback.setup()
        motor.setup()
        run()
    except KeyboardInterrupt:
        print("\n[EXIT] Interrupted.")
    finally:
        motor.cleanup()
        GPIO.cleanup()
