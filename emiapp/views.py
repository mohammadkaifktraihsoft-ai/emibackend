from django.http import JsonResponse
from rest_framework import viewsets, generics, permissions, status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User
from .models import Customer, EMI, Payment, UserProfile, Device, BalanceKey
from django.utils import timezone
from .serializers import (
    CustomerSerializer,
    EMISerializer,
    PaymentSerializer,
    SignUpSerializer,
    UserProfileSerializer,
    DeviceSerializer,
    BalanceKeySerializer,
)

# ---------------- PING TEST ----------------
def ping(request):
    return JsonResponse({"message": "pong"})

# ---------------- SIGNUP ----------------
class SignUpView(generics.CreateAPIView):
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]


# ---------------- LOGIN ----------------
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["username"] = self.user.username
        data["email"] = self.user.email
        return data


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ---------------- USER PROFILE ----------------
class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------- CUSTOMERS ----------------
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Customer.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------- DEVICE LOCK/UNLOCK ----------------

# ✅ 1. Register Device (called from client app)
def register_device(request):
    key_value = request.data.get("key")
    imei = request.data.get("imei")
    name = request.data.get("name")
    mobile = request.data.get("mobile")

    if not key_value:
        return Response({"error": "Balance key is required"}, status=status.HTTP_400_BAD_REQUEST)
    if not imei:
        return Response({"error": "IMEI is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        balance_key = BalanceKey.objects.get(key=key_value, is_used=False)
    except BalanceKey.DoesNotExist:
        return Response({"error": "Invalid or already used balance key"}, status=status.HTTP_400_BAD_REQUEST)

    customer = Customer.objects.create(
        user=balance_key.admin_user,
        name=name,
        mobile=mobile,
        imei_1=imei,
    )

    balance_key.is_used = True
    balance_key.used_by = customer
    balance_key.used_at = timezone.now()
    balance_key.save()

    return Response({
        "message": "Device registered successfully",
        "admin_user": balance_key.admin_user.username,
        "customer_id": customer.id
    }, status=status.HTTP_201_CREATED)

# ✅ 2. Lock Device (called from admin app)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def lock_device(request):
    imei = request.data.get("imei")
    if not imei:
        return Response({"error": "IMEI is required"}, status=400)

    try:
        device = Device.objects.get(imei=imei)
        device.is_locked = True
        device.save()
        return Response({"message": "Device locked successfully"}, status=200)
    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)


# ✅ 3. Unlock Device (called from admin app)
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def unlock_device(request):
    imei = request.data.get("imei")
    if not imei:
        return Response({"error": "IMEI is required"}, status=400)

    try:
        device = Device.objects.get(imei=imei)
        device.is_locked = False
        device.save()
        return Response({"message": "Device unlocked successfully"}, status=200)
    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)

#------------------ balance key  ----------------
class BalanceKeyViewSet(viewsets.ModelViewSet):
    serializer_class = BalanceKeySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BalanceKey.objects.filter(admin_user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(admin_user=self.request.user)


# ---------------- EMIs ----------------
class EMIViewSet(viewsets.ModelViewSet):
    queryset = EMI.objects.all()
    serializer_class = EMISerializer


# ---------------- PAYMENTS ----------------
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
