from django.urls import path, include
from rest_framework import routers
from . import views_balancekey
from .views import (
    ping,
    SignUpView,
    LoginView,
    CustomerViewSet,
    EMIViewSet,
    PaymentViewSet,
    UserProfileViewSet,
    register_device,
    lock_device,
    unlock_device,
    
    
)

router = routers.DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'emis', EMIViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'user-profile', UserProfileViewSet, basename='user-profile')




urlpatterns = [
    path('ping/', ping, name='ping'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),

    # ✅ Device control APIs (for client app)
    path("device/register/", register_device, name="register-device"),
    path("device/lock/", lock_device, name="lock-device"),
    path("device/unlock/", unlock_device, name="unlock-device"),
    # balance key api
    path("balance-keys/", views_balancekey.BalanceKeyListCreateView.as_view(), name="balance-key-list"),

    # ✅ All router-based API endpoints (customers, EMI, payments, etc.)
    path('', include(router.urls)),
]
