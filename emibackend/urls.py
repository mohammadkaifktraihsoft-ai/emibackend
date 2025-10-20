from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static
from emiapp import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('emiapp.urls')),   # include app URLs 
    path('api/v1/signup/', views.SignUpView.as_view(), name='signup'), 
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

     path('api-auth/', include('rest_framework.urls')),
]

# Serve media files (for profile & QR uploads)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
