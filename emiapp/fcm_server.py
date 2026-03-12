import os
import json
import firebase_admin
from firebase_admin import credentials, messaging


# --------- INITIALIZE FIREBASE USING ENV VARIABLE ----------
def initialize_firebase():
    if not firebase_admin._apps:
        service_account_info = json.loads(os.environ["serviceaccountkey"])  # your ENV NAME
        cred = credentials.Certificate(service_account_info)
        firebase_admin.initialize_app(cred)


initialize_firebase()


# --------- FUNCTION TO SEND COMMAND TO DEVICE ----------
def send_command(token, command):
    try:
        if not token:
            print("FCM ERROR: Token is empty")
            return None

        message = messaging.Message(
            data={"command": command},
            token=token,
        )

        response = messaging.send(message)
        print("FCM Message sent:", response)
        return response

    except Exception as e:
        print("FCM ERROR:", str(e))
        return None


# --------- TEST USAGE (OPTIONAL) ----------
if __name__ == "__main__":
    device_token = "FCM-TOKEN-FROM-ANDROID"
    send_command(device_token, "LOCK")
