from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, EMI, Payment, UserProfile

# ---------------- SIGNUP & LOGIN ----------------

class SignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        # Use create_user to hash the password
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        return user

# ---------------- USER PROFILE SERIALIZER ----------------
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = "__all__"

# ---------------- EMI SERIALIZER ----------------
class EMISerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = EMI
        fields = '__all__'

# ---------------- CUSTOMER SERIALIZER ----------------
class CustomerSerializer(serializers.ModelSerializer):
    emis = serializers.SerializerMethodField()  # include only first EMI

    class Meta:
        model = Customer
        fields = '__all__'

    def get_emis(self, obj):
        """
        Return only the first EMI per customer.
        """
        first_emi = obj.emis.all().order_by('id').first()
        if first_emi:
            return EMISerializer(first_emi).data
        return []

# ---------------- PAYMENT SERIALIZER ----------------
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
