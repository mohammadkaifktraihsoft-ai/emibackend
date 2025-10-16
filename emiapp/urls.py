from django.urls import path, include
from rest_framework import routers
from .views import (
    CustomerViewSet,
    EMIViewSet,
    PaymentViewSet,
    UserProfileViewSet,
    SignUpView,
    LoginView,
    ping,
)

router = routers.DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'emis', EMIViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'userprofile', UserProfileViewSet, basename='userprofile')

urlpatterns = [
    path('ping/', ping, name='ping'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('', include(router.urls)),
]
