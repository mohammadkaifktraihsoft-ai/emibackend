from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Customer, EMI, Payment, UserProfile


# ----------- USER PROFILE -----------
class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'username', 'email', 'profile_image', 'qr_image',
            'shop_name', 'distributor_name', 'distributor_contact'
        ]

# ----------- EMI -----------
class EMISerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = EMI
        fields = '__all__'

# ----------- CUSTOMER -----------
class CustomerSerializer(serializers.ModelSerializer):
    emis = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = '__all__'

    def get_emis(self, obj):
        first_emi = obj.emis.all().order_by('id').first()
        if first_emi:
            return EMISerializer(first_emi).data
        return []

# ----------- PAYMENT -----------
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
