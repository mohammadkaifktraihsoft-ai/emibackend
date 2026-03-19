import hmac
import hashlib
from datetime import datetime

def generate_unlock_code(secret, imei):
    try:
        # ensure string
        secret = str(secret)
        imei = str(imei)

        # fixed date format
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

        message = (imei + date_str).encode()
        key = secret.encode()

        h = hmac.new(key, message, hashlib.sha256).hexdigest()

        return h[-6:]  # last 6 digits

    except Exception as e:
        print("Unlock code error:", str(e))
        return "000000"  # fallback (never crash)