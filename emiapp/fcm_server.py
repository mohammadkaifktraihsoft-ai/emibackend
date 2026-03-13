import os
import json
import firebase_admin
from firebase_admin import credentials, messaging


# Initialize Firebase once when server starts
if not firebase_admin._apps:
    service_account_info = json.loads(os.environ["serviceaccountkey"])
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

print(firebase_admin.get_app().credential.service_account_email)
# Function to send command
def send_command(token, command):
    try:
        if not token:
            return {"error": "FCM token missing"}

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