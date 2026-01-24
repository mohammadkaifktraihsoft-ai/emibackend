from django.http import JsonResponse
from django.utils.timezone import now
from django.db.models import F, Q
from django.db import transaction
from rest_framework import viewsets, generics, permissions, status
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.throttling import ScopedRateThrottle
from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone
import logging

from .models import Customer, EMI, Payment, UserProfile, Device, BalanceKey, FCM
from .serializers import (
    CustomerSerializer,
    EMISerializer,
    PaymentSerializer,
    SignUpSerializer,
    UserProfileSerializer,
    DeviceSerializer,
    BalanceKeySerializer,
)

logger = logging.getLogger(__name__)

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
    throttle_scope = 'login'
    throttle_classes = [ScopedRateThrottle]

# ---------------- USER PROFILE ----------------
class UserProfileViewSet(viewsets.ModelViewSet):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    queryset = UserProfile.objects.none()  # required for router

    def get_queryset(self):
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# ---------------- CUSTOMERS ----------------
class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.none()  # required for router

    def get_queryset(self):
        if self.request.user.is_staff:
            return Customer.objects.all().order_by("-created_at")
        return Customer.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# ---------------- UPDATE EMI (ADMIN ONLY) ----------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_emi_payment(request, customer_id):
    if not request.user.is_staff:
        return Response({"detail": "Admin only"}, status=403)

    try:
        with transaction.atomic():
            # Lock customer row
            customer = Customer.objects.select_for_update().get(id=customer_id)
            if customer.paid_months >= (customer.total_months or 0):
                return Response({"message": "All EMI already paid"}, status=400)

            # Atomic update
            customer.paid_months = F('paid_months') + 1
            customer.remaining_months = F('total_months') - F('paid_months') - 1
            customer.next_payment_date = (
                customer.next_payment_date + timedelta(days=30)
                if customer.next_payment_date
                else now().date() + timedelta(days=30)
            )
            customer.save()
            customer.refresh_from_db()  # 🔄 refresh actual values

            # Lock and update EMI row
            emi = EMI.objects.select_for_update().filter(customer=customer, is_closed=False).first()
            if emi:
                emi.paid_amount += customer.emi_per_month or 0
                if emi.paid_amount >= emi.total_amount:
                    emi.is_closed = True
                emi.save()
                Payment.objects.create(emi=emi, amount=customer.emi_per_month or 0)

            return Response({
                "message": "EMI updated",
                "paid_months": customer.paid_months,
                "remaining_months": customer.remaining_months
            })
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)

# ---------------- PENDING EMI (ADMIN + CUSTOMER) ----------------
class PendingEMIViewSet(ReadOnlyModelViewSet):
    serializer_class = EMISerializer
    permission_classes = [IsAuthenticated]
    queryset = EMI.objects.none()  # required for router

    def get_queryset(self):
        user = self.request.user
        imei = self.request.headers.get("X-IMEI")

        # Validate IMEI format
        if imei and (len(imei) not in (15, 16) or not imei.isdigit()):
            raise PermissionDenied("Invalid IMEI format")

        if user.is_staff:
            return EMI.objects.filter(is_closed=False).order_by("next_due_date")

        if not imei:
            raise PermissionDenied("IMEI required")

        try:
            device = Device.objects.get(imei=imei, customer__user=user)
        except Device.DoesNotExist:
            raise PermissionDenied("Unauthorized device")

        return EMI.objects.filter(customer=device.customer, is_closed=False).order_by("next_due_date")

# ---------------- DEVICE LOCK/UNLOCK ----------------
@api_view(["POST"])
@permission_classes([AllowAny])
def register_device(request):
    key_value = request.data.get("key")
    imei = request.data.get("imei")

    if not key_value:
        return Response({"error": "Balance key is required"}, status=400)
    if not imei or len(imei) not in (15, 16) or not imei.isdigit():
        return Response({"error": "Valid IMEI required"}, status=400)

    try:
        customer = Customer.objects.get(Q(imei_1=imei) | Q(imei_2=imei))
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)

    try:
        balance_key = BalanceKey.objects.get(key=key_value, is_used=False)
    except BalanceKey.DoesNotExist:
        return Response({"error": "Invalid or used key"}, status=400)

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

    balance_key.is_used = True
    balance_key.used_by = customer
    balance_key.used_at = timezone.now()
    balance_key.save()

    return Response({"message": "Device registered successfully"}, status=201)


# ---------------- GET CUSTOMER DATA (FOR DEVICE) ----------------
@api_view(["GET"])
@permission_classes([AllowAny])  # Allow access without JWT
def get_customer_data(request):
    imei = request.headers.get("X-IMEI")  # Device sends its IMEI in header
    if not imei:
        return Response({"error": "IMEI required"}, status=400)

    try:
        device = Device.objects.get(imei=imei)
        customer = device.customer
    except Device.DoesNotExist:
        return Response({"error": "Device not registered"}, status=403)

    # Return only the data for this customer
    return Response({
        "id": customer.id,
        "name": customer.name,
        "mobile": customer.mobile,
        "email": customer.email,
        "total_emi_amount": customer.total_emi_amount,
        "emi_per_month": customer.emi_per_month,
        "paid_months": customer.paid_months,
        "remaining_months": customer.remaining_months,
        "next_payment_date": customer.next_payment_date
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def lock_device(request):
    if not request.user.is_staff:
        return Response({"detail": "Admin only"}, status=403)

    imei = request.data.get("imei")
    if not imei:
        return Response({"error": "IMEI is required"}, status=400)

    try:
        device = Device.objects.get(imei=imei)
        device.is_locked = True
        device.last_action = "locked"
        device.last_updated = timezone.now()
        device.save()

        # Logging
        logger.info(f"{request.user.username} locked device {imei} at {timezone.now()}")

        return Response({"message": "Device locked successfully"}, status=200)
    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unlock_device(request):
    if not request.user.is_staff:
        return Response({"detail": "Admin only"}, status=403)

    imei = request.data.get("imei")
    if not imei:
        return Response({"error": "IMEI is required"}, status=400)

    try:
        device = Device.objects.get(imei=imei)
        device.is_locked = False
        device.last_action = "unlocked"
        device.last_updated = timezone.now()
        device.save()

        # Logging
        logger.info(f"{request.user.username} unlocked device {imei} at {timezone.now()}")

        return Response({"message": "Device unlocked successfully"}, status=200)
    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)

# ---------------- BALANCE KEYS ----------------
class BalanceKeyViewSet(viewsets.ModelViewSet):
    serializer_class = BalanceKeySerializer
    permission_classes = [IsAuthenticated]
    queryset = BalanceKey.objects.none()  # required for router

    def get_queryset(self):
        return BalanceKey.objects.filter(admin_user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(admin_user=self.request.user)

# ---------------- EMIs ----------------
class EMIViewSet(viewsets.ModelViewSet):
    serializer_class = EMISerializer
    permission_classes = [IsAuthenticated]
    queryset = EMI.objects.none()  # required for router

    def get_queryset(self):
        user = self.request.user
        imei = self.request.headers.get("X-IMEI")
        if user.is_staff:
            return EMI.objects.all()
        try:
            device = Device.objects.get(imei=imei, customer__user=user)
        except Device.DoesNotExist:
            raise PermissionDenied("Unauthorized device")
        return EMI.objects.filter(customer=device.customer)

# ---------------- PAYMENTS ----------------
class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    queryset = Payment.objects.none()  # required for router

    def get_queryset(self):
        user = self.request.user
        imei = self.request.headers.get("X-IMEI")
        if user.is_staff:
            return Payment.objects.all()
        try:
            device = Device.objects.get(imei=imei, customer__user=user)
        except Device.DoesNotExist:
            raise PermissionDenied("Unauthorized device")
        return Payment.objects.filter(emi__customer=device.customer)

# ---------------- FCM TOKEN ----------------
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_fcm_token(request):
    imei_1 = request.data.get("imei_1")
    fcm_token = request.data.get("fcm_token")

    if not imei_1 or not fcm_token:
        return Response({"error": "imei_1 and fcm_token required"}, status=400)

    # Verify ownership
    if not Customer.objects.filter(user=request.user, imei_1=imei_1).exists():
        return Response({"error": "Unauthorized or IMEI not found"}, status=403)

    FCM.objects.update_or_create(
        imei_1=imei_1,
        defaults={"fcm_token": fcm_token}
    )
    return Response({"message": "Token updated"})
