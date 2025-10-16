from rest_framework import routers
from .views import CustomerViewSet, EMIViewSet,PaymentViewSet ,ping
from django.urls import path, include

router = routers.DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'emis', EMIViewSet)
router.register(r'payments', PaymentViewSet)


urlpatterns = [
    path('ping/', ping),           # your ping endpoint
    path('', include(router.urls)) # include all router URLs
    
]
