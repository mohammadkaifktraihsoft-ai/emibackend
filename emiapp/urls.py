from django.urls import path, include
from rest_framework import routers
from . import views_balancekey
from .views import device_customer_data, update_emi_payment
from .views import update_fcm_token
from .views import get_unlock_code
from django.conf import settings
from django.conf.urls.static import static
from .views import admin_get_unlock_code
from .views import MDMQRView
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
    PendingEMIViewSet,
    TutorialListView,
    MDMQRView,
    MDMConfigCreateView,
    PolicyListView,
    PolicyUpdateView,
    ServiceRequestCreateView,
    LatestAppVersionView,

)

router = routers.DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'emis', EMIViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'user-profile', UserProfileViewSet, basename='user-profile')
router.register(r'pending-emis', PendingEMIViewSet, basename='pending-emis')

    


urlpatterns = [
    path('ping/', ping, name='ping'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),

    # ✅ Device control APIs (for client app)
    path("device/register/", register_device, name="register-device"),
    path("device/customer/", device_customer_data),
    path("device/lock/", lock_device, name="lock-device"),
    path("device/unlock/", unlock_device, name="unlock-device"),
    path("device/<str:imei>/unlock-code/", get_unlock_code, name="get-unlock-code"),
    path("admin/device/<str:imei>/unlock-code/", admin_get_unlock_code),
    # balance key api
    path("balance-keys/", views_balancekey.BalanceKeyListCreateView.as_view(), name="balance-key-list"),
    path('update-emi/<int:customer_id>/', update_emi_payment, name='update_emi'),
    # ✅ All router-based API endpoints (customers, EMI, payments, etc.)
    path('', include(router.urls)),
    path('device/update-fcm-token/', update_fcm_token),
    path("tutorials/", TutorialListView),
    # MDM APIs
    path("mdm/qr/", MDMQRView.as_view()),
    path("policies/", PolicyListView.as_view(), name="policies"),
    path("admin/policies/", PolicyUpdateView.as_view()),
    path("service-requests/", ServiceRequestCreateView.as_view(), name="service-request"),
     path("app/version/", LatestAppVersionView.as_view(), name="app-version"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)