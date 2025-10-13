from rest_framework import routers
from .views import CustomerViewSet, EMIViewSet

router = routers.DefaultRouter()
router.register(r'customers', CustomerViewSet)
router.register(r'emis', EMIViewSet)

urlpatterns = router.urls
