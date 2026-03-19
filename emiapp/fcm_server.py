import os
import json
import firebase_admin
from firebase_admin import credentials, messaging

firebase_app = None


def initialize_firebase():
    global firebase_app

    # Already initialized
    if firebase_app:
        return firebase_app

    if firebase_admin._apps:
        firebase_app = firebase_admin.get_app()
        return firebase_app

    # Check env variable
    service_account = os.environ.get("serviceaccountkey")

    if not service_account:
        print("⚠️ Firebase key not found (safe for migration)")
        return None

    try:
        service_account_info = json.loads(service_account)
        cred = credentials.Certificate(service_account_info)
        firebase_app = firebase_admin.initialize_app(cred)

        print("✅ Firebase initialized")
        return firebase_app

    except Exception as e:
        print("❌ Firebase init error:", str(e))
        return None


# Function to send command
def send_command(token, command):
    try:
        if not token:
            return {"error": "FCM token missing"}

        app = initialize_firebase()

        if not app:
            return {"error": "Firebase not initialized"}

        message = messaging.Message(
            data={"command": command},
            token=token,
        )

        response = messaging.send(message)
        print("FCM sent:", response)

        return {"success": response}

    except Exception as e:
        print("FCM ERROR:", str(e))
        return {"error": str(e)}