from rest_framework import generics, permissions
from .models import BalanceKey
from .serializers import BalanceKeySerializer

class BalanceKeyListCreateView(generics.ListCreateAPIView):
    queryset = BalanceKey.objects.all()
    serializer_class = BalanceKeySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Show only keys for the logged-in admin
        return BalanceKey.objects.filter(admin_user=self.request.user)

    def perform_create(self, serializer):
        # Auto-assign key to logged-in admin
        serializer.save(admin_user=self.request.user)
