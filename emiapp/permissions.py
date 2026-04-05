from rest_framework.permissions import BasePermission
from .models import Device

class IsDeviceAuthenticated(BasePermission):
    def has_permission(self, request, view):
        token = request.headers.get("Authorization")

        if not token or not token.startswith("Device "):
            return False

        parts = token.split()

        if len(parts) != 2:
            return False

        token_value = parts[1]

        try:
            device = Device.objects.get(device_token=token_value)

            # Optional checks
            # if not device.is_active:
            #     return False

            request.device = device
            return True

        except Device.DoesNotExist:
            return False