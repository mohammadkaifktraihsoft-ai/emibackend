from django.http import JsonResponse
from rest_framework import viewsets, generics, permissions, status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.models import User
from .models import Customer, EMI, Payment, UserProfile, Device, BalanceKey
from datetime import timedelta
from django.utils.timezone import now
from django.db.models import Q
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


@api_view(["POST"])
def update_emi_payment(request, customer_id):
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

    # Optional data from request (if sent)
    paid_months = customer.paid_months or 0
    total_months = customer.total_months or 0

    # ✅ Prevent over-payment
    if paid_months >= total_months and total_months != 0:
        return Response({"message": "All EMI already paid."}, status=status.HTTP_400_BAD_REQUEST)

    # ✅ Increase EMI month
    customer.paid_months = paid_months + 1
    customer.remaining_months = total_months - customer.paid_months

    if customer.next_payment_date:
        customer.next_payment_date += timedelta(days=30)
    else:
        customer.next_payment_date = now().date() + timedelta(days=30)

    customer.save()

    return Response({
        "message": "EMI updated successfully",
        "paid_months": customer.paid_months,
        "remaining_months": customer.remaining_months,
        "next_payment_date": customer.next_payment_date
    }, status=status.HTTP_200_OK)


# ---------------- DEVICE LOCK/UNLOCK ----------------

# ✅ 1. Register Device (called from client app)
@api_view(["POST"])
def register_device(request):
    key_value = request.data.get("key")
    imei = request.data.get("imei")

    # New customer / EMI details
    name = request.data.get("name")
    mobile = request.data.get("mobile")
    mobile_model = request.data.get("mobile_model")
    total_emi = request.data.get("total_emi_amount")
    emi_monthly = request.data.get("emi_per_month")
    total_months = request.data.get("total_months")
    next_payment_date = request.data.get("next_payment_date")

    if not key_value:
        return Response({"error": "Balance key is required"}, status=400)

    if not imei:
        return Response({"error": "IMEI is required"}, status=400)

    # ✔ Find customer by ANY IMEI (imei_1 or imei_2)
    try:
        customer = Customer.objects.get(Q(imei_1=imei) | Q(imei_2=imei))
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)

    # ✔ Validate balance key
    try:
        balance_key = BalanceKey.objects.get(key=key_value, is_used=False)
    except BalanceKey.DoesNotExist:
        return Response({"error": "Invalid or used key"}, status=400)

    # ✔ Update customer EMI details (if provided)
    customer.name = name or customer.name
    customer.mobile = mobile or customer.mobile
    customer.mobile_model = mobile_model or customer.mobile_model
    customer.total_emi_amount = total_emi or customer.total_emi_amount
    customer.emi_per_month = emi_monthly or customer.emi_per_month
    customer.total_months = total_months or customer.total_months
    customer.next_payment_date = next_payment_date or customer.next_payment_date
    customer.save()

    # ✔ Create or update the DEVICE entry
    device, created = Device.objects.update_or_create(
        imei=imei,
        defaults={
            "customer": customer,
            "user": balance_key.admin_user,
            "is_locked": False,
            "last_action": "registered",
            "last_updated": timezone.now()
        }
    )

    # ✔ Mark key as used
    balance_key.is_used = True
    balance_key.used_by = customer
    balance_key.used_at = timezone.now()
    balance_key.save()

    return Response({"message": "Device registered successfully"}, status=201)


# 🔒 Lock Device
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def lock_device(request):
    imei = request.data.get("imei")
    if not imei:
        return Response({"error": "IMEI is required"}, status=400)

    try:
        device = Device.objects.get(imei=imei)
    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)

    device.is_locked = True
    device.last_action = "locked"
    device.last_updated = timezone.now()
    device.save()

    return Response({"message": "Device locked successfully"}, status=200)


# 🔓 Unlock Device
@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def unlock_device(request):
    imei = request.data.get("imei")
    if not imei:
        return Response({"error": "IMEI is required"}, status=400)

    try:
        device = Device.objects.get(imei=imei)
    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)

    device.is_locked = False
    device.last_action = "unlocked"
    device.last_updated = timezone.now()
    device.save()

    return Response({"message": "Device unlocked successfully"}, status=200)


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
