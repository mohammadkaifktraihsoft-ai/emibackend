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
from .fcm_server import send_command 
import logging
import traceback
from rest_framework.views import APIView
from .models import Device, FCM
from .utils import generate_code
from django.shortcuts import get_object_or_404
from .models import Customer, EMI, Payment, UserProfile, Device, BalanceKey, FCM
from .serializers import (
    CustomerSerializer,
    EMISerializer,
    PaymentSerializer,
    SignUpSerializer,
    UserProfileSerializer,
    DeviceSerializer,
    BalanceKeySerializer,
    MDMConfigSerializer,
)
from .models import MDMConfig

from .models import Tutorial
from .serializers import TutorialSerializer
from .permissions import IsDeviceAuthenticated
from rest_framework.generics import ListAPIView
import uuid
logger = logging.getLogger(__name__)
from .models import Policy
from .serializers import PolicySerializer
from .models import ServiceRequest
from .serializers import ServiceRequestSerializer
from .serializers import MDMConfigSerializer

from .models import AppVersion
from .serializers import AppVersionSerializer
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
    queryset = Customer.objects.none()

    def get_queryset(self):   # ✅ inside function
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
            customer = Customer.objects.select_for_update().get(id=customer_id, user=request.user)
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
    key_value = request.data.get("key", "").strip()
    imei = request.data.get("imei", "").strip()

    # ✅ Validate inputs
    if not key_value:
        return Response({"error": "Balance key is required"}, status=400)

    if not imei or len(imei) not in (15, 16) or not imei.isdigit():
        return Response({"error": "Valid IMEI required"}, status=400)

    # ✅ Validate UUID format (VERY IMPORTANT)
    try:
        uuid.UUID(key_value)
    except ValueError:
        return Response({"error": "Invalid balance key format"}, status=400)

    # ✅ Get customer
    try:
        customer = Customer.objects.get(Q(imei_1=imei) | Q(imei_2=imei))
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)

    # ✅ Safe query (no crash)
    balance_key = BalanceKey.objects.filter(key=key_value).first()

    if not balance_key:
        return Response({"error": "Balance key not found"}, status=400)

    if balance_key.is_used:
        return Response({"error": "Balance key already used"}, status=400)

    if not balance_key.admin_user:
        return Response({"error": "Balance key missing admin"}, status=400)

    # ✅ Register device
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

    if not device.device_token:
        device.device_token = uuid.uuid4()
        device.save(update_fields=["device_token"])

    # ✅ Mark key used
    balance_key.is_used = True
    balance_key.used_by = customer
    balance_key.used_at = timezone.now()
    balance_key.save()

    return Response({
        "message": "Device registered successfully",
        "device_token": str(device.device_token)
    }, status=201)


# ---------------- GET CUSTOMER DATA (FOR DEVICE) ----------------
@api_view(["GET"])
@permission_classes([IsDeviceAuthenticated])
def device_customer_data(request):
    device = request.device  # ✅ use authenticated device

    customer = device.customer

    if not customer:
        return Response({"error": "No customer linked"}, status=404)

    return Response({
        "id": customer.id,
        "name": customer.name,
        "mobile": customer.mobile,
        "email": customer.email,
        "total_emi_amount": customer.total_emi_amount,
        "emi_per_month": customer.emi_per_month,
        "paid_months": customer.paid_months,
        "remaining_months": customer.remaining_months,
        "next_payment_date": customer.next_payment_date,
        "dealer_contact": customer.dealer_contact,
        "paid_down_payment": customer.paid_down_payment,
    })

# ---------------- LOCK DEVICE ----------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def lock_device(request):
    if not request.user.is_staff:
        return Response({"detail": "Admin only"}, status=403)

    imei = request.data.get("imei")
    if not imei:
        return Response({"error": "IMEI is required"}, status=400)

    try:
        device = Device.objects.get(imei=imei,user=request.user)

        # 🔒 Lock device
        device.is_locked = True
        device.last_action = "locked"
        device.last_updated = timezone.now()
        

        # 🔑 Generate offline unlock code
        unlock_code = generate_code()
        device.unlock_code = unlock_code

        device.save()
        # 📡 Send FCM lock command
        try:
            fcm_entry = FCM.objects.get(imei_1=imei)
            if fcm_entry.fcm_token:
                result = send_command(fcm_entry.fcm_token, "LOCK")
                logger.info(f"FCM command result: {result}")
        except FCM.DoesNotExist:
            logger.warning(f"No FCM token found for device {imei}")

        # 📝 Logging
        logger.info(f"{request.user.username} locked device {imei} at {timezone.now()}")

        return Response({
            "message": "Device locked successfully",
            "imei": imei,
            "unlock_code": unlock_code
        }, status=200)

    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)
# ---------------- UNLOCK DEVICE ----------------
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def unlock_device(request):
    if not request.user.is_staff:
        return Response({"detail": "Admin only"}, status=403)

    imei = request.data.get("imei")
    if not imei:
        return Response({"error": "IMEI is required"}, status=400)

    try:
        device = Device.objects.get(imei=imei,user=request.user)

        device.is_locked = False
        device.last_action = "unlocked"
        device.last_updated = timezone.now()
        device.save()

        # Lookup FCM token from FCM table
        try:
            fcm_entry = FCM.objects.get(imei_1=imei)
            if fcm_entry.fcm_token:
                result = send_command(fcm_entry.fcm_token, "UNLOCK")
                logger.info(f"FCM command result: {result}")
        except FCM.DoesNotExist:
            logger.warning(f"No FCM token found for device {imei}")

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
@api_view(["POST"])
@permission_classes([IsDeviceAuthenticated])
def update_fcm_token(request):
    device = request.device

    fcm_token = request.data.get("fcm_token")

    if not fcm_token:
        return Response({"error": "fcm_token required"}, status=400)

    FCM.objects.update_or_create(
        imei_1=device.imei,
        defaults={"fcm_token": fcm_token}
    )

    return Response({"message": "FCM token updated"})

#---------------- TUTORIAL ----------------

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def TutorialListView(request):
    tutorials = Tutorial.objects.all()
    serializer = TutorialSerializer(tutorials, many=True)
    return Response(serializer.data)
#---------------- UTILS ----------------



@api_view(["GET"])
@permission_classes([IsDeviceAuthenticated])
def get_unlock_code(request, imei):
    device = request.device  # from permission

    # 🔒 Ensure device matches IMEI
    if device.imei != imei:
        return Response({"error": "Unauthorized device"}, status=403)

    return Response({
    "imei": device.imei,
    "unlock_code": device.unlock_code
    })
    

#---------------- ADMIN GET UNLOCK CODE ----------------
@api_view(["GET"])
@permission_classes([IsAuthenticated])  # ✅ Admin JWT auth
def admin_get_unlock_code(request, imei):
    try:
        device = Device.objects.get(imei=imei,user=request.user)

        # Optional safety checks
        if not device.is_locked:
            return Response({"error": "Device is not locked"}, status=400)

        if not device.unlock_code:
            return Response({"error": "No unlock code available"}, status=404)

        return Response({
            "imei": device.imei,
            "unlock_code": device.unlock_code
        })

    except Device.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)

#---------------- MDM CONFIG ----------------
class MDMQRView(APIView):
    permission_classes = [IsAuthenticated]   # 🔒 require login

    def get(self, request):
        config = MDMConfig.objects.first()

        if not config:
            return Response({"error": "No config found"}, status=404)

        serializer = MDMConfigSerializer(config)

        return Response(serializer.data)


#---------------- MDM CONFIG CREATE (ADMIN ONLY) ----------------
class MDMConfigCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAdminUser]  # ✅ only admin can create
    queryset = MDMConfig.objects.all()
    serializer_class = MDMConfigSerializer


#---------------- POLICY LIST ----------------
class PolicyUpdateView(APIView):
    permission_classes = [IsAuthenticated]  # ✅ only admin

    def post(self, request):
        policy_type = request.data.get("type")
        content = request.data.get("content")

        policy, created = Policy.objects.update_or_create(
            type=policy_type,
            defaults={"content": content}
        )

        return Response({
            "message": "Policy updated",
            "type": policy.type
        })



class PolicyListView(ListAPIView):
    queryset = Policy.objects.all()
    serializer_class = PolicySerializer
    permission_classes = [AllowAny]  # ✅ public access


#---------------- SERVICE REQUEST CREATE (for future use) ----------------
class ServiceRequestCreateView(generics.CreateAPIView):
    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()



#---------------- LATEST APP VERSION ----------------

class LatestAppVersionView(APIView):
    def get(self, request):
        latest = AppVersion.objects.order_by("-version_code").first()

        if not latest:
            return Response({"message": "No version found"}, status=404)

        serializer = AppVersionSerializer(latest)
        return Response(serializer.data)