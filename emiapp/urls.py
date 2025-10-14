from rest_framework import routers
from .views import CustomerViewSet, EMIViewSet, ping
from django.urls import path, include

router = routers.DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'emis', EMIViewSet)

urlpatterns = [
    path('ping/', ping),           # your ping endpoint
    path('', include(router.urls)) # include all router URLs
]
