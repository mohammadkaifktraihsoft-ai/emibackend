import hmac
import hashlib
import time

TIME_STEP = 30  # seconds
CODE_LENGTH = 6  # change to 8 if needed


def generate_unlock_code(secret, imei):
    timestep = int(time.time() / TIME_STEP)

    message = f"{imei}{timestep}".encode()
    key = secret.encode()

    h = hmac.new(key, message, hashlib.sha256).hexdigest()

    return str(int(h, 16))[-CODE_LENGTH:]