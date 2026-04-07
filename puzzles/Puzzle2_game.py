import time
from config import SECRET_CODE, MAX_ATTEMPTS, LOCKOUT_SECONDS, INPUT_TIMEOUT_SEC
import keypad, feedback, motor

def run():
    attempts = 0

    while True:
        if attempts >= MAX_ATTEMPTS:
            feedback.lockout(LOCKOUT_SECONDS)
            attempts = 0

        print(f"\n[PUZZLE 2] Enter the 4-digit code (attempt {attempts + 1}/{MAX_ATTEMPTS}):")
        entered = _collect_digits()

        if entered is None:
            print("[TIMEOUT] No input received, resetting.")
            feedback.wrong_code()
            attempts += 1
            continue

        if entered == SECRET_CODE:
            print("[SUCCESS] Correct code!")
            feedback.success()
            motor.open_door()
            print("[DONE] Compartment unlocked. Puzzle 2 complete.")
            break
        else:
            print(f"[WRONG] Got '{entered}', expected '{SECRET_CODE}'")
            feedback.wrong_code()
            attempts += 1

def _collect_digits():
    """Read exactly 4 digits from keypad. Returns string or None on timeout."""
    digits = []
    deadline = time.time() + INPUT_TIMEOUT_SEC

    while len(digits) < 4:
        remaining = deadline - time.time()
        if remaining <= 0:
            return None

        key = keypad.read_key(timeout=min(remaining, 5.0))

        if key is None:
            continue                      # Keep waiting until full timeout
        if not key.isdigit():
            continue                      # Ignore *, #, A-D

        digits.append(key)
        print(f"  Digit {len(digits)}: *")
        feedback.digit_ok()

    return "".join(digits)
