from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, EMI, Payment, UserProfile

# ---------------- SIGNUP & LOGIN ----------------
class SignUpSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(write_only=True, required=True)
    shop_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "phone_number", "shop_name")
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def create(self, validated_data):
        phone_number = validated_data.pop("phone_number", None)
        shop_name = validated_data.pop("shop_name", "")

        # ✅ Create and activate user
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=validated_data["password"],
            is_staff=True,
        )
        user.is_active = True  # make user immediately active
        user.save()

        # ✅ Create or update the user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.phone_number = phone_number
        profile.shop_name = shop_name
        profile.save()

        return user



# ---------------- USER PROFILE SERIALIZER ----------------
class UserProfileSerializer(serializers.ModelSerializer):
    # Include username and email from the related User model
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = UserProfile
        fields = (
            "username",
            "email",
            "phone_number",
            "shop_name",
            "distributor_name",
            "distributor_contact",
            "profile_image",
            "qr_image",
        )

# ---------------- EMI SERIALIZER ----------------
class EMISerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = EMI
        fields = '__all__'

# ---------------- CUSTOMER SERIALIZER ----------------
class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = '__all__'

# ---------------- PAYMENT SERIALIZER ----------------
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
