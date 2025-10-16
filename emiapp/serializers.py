from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, EMI, Payment, UserProfile

# ---------------- SIGNUP SERIALIZER ----------------
class SignUpSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password']
        )
        # Automatically create an empty profile
        UserProfile.objects.create(user=user)
        return user


# ---------------- USER PROFILE SERIALIZER ----------------
class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'username', 'email', 'profile_image', 'qr_image',
            'shop_name', 'distributor_name', 'distributor_contact'
        ]


# ---------------- EMI SERIALIZER ----------------
class EMISerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = EMI
        fields = '__all__'


# ---------------- CUSTOMER SERIALIZER ----------------
class CustomerSerializer(serializers.ModelSerializer):
    emis = serializers.SerializerMethodField()  # custom field to filter EMIs

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
