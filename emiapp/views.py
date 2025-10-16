from django.http import JsonResponse
from rest_framework import viewsets, generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Customer, EMI, Payment, UserProfile
from .serializers import (
    CustomerSerializer,
    EMISerializer,
    PaymentSerializer,
    SignUpSerializer,
    UserProfileSerializer,
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
    """Extend token serializer to include username in response"""
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
        # Only return the profile for the logged-in user
        return UserProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ---------------- CUSTOMERS ----------------
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer


# ---------------- EMIs ----------------
class EMIViewSet(viewsets.ModelViewSet):
    queryset = EMI.objects.all()
    serializer_class = EMISerializer


# ---------------- PAYMENTS ----------------
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
