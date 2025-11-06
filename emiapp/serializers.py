from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, EMI, Payment, UserProfile, Device, BalanceKey 


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

# ---------------- DEVICE SERIALIZER ----------------
class DeviceSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Device
        fields = [
            "id",
            "user_name",
            "customer_name",
            "imei",
            "is_locked",
            "registered_at",
        ]
        read_only_fields = ["id", "registered_at", "user_name", "customer_name"]

# ---------------- BALANCE KEY SERIALIZER ----------------


class BalanceKeySerializer(serializers.ModelSerializer):
    admin_username = serializers.CharField(source='admin_user.username', read_only=True)
    qr_image = serializers.ImageField(read_only=True)

    class Meta:
        model = BalanceKey
        fields = [
            "id",
            "key",
            "admin_username",
            "is_used",
            "used_by",
            "qr_image",
            "created_at",
            "used_at",
        ]



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
        fields = [
            "id",
            "name",
            "mobile",
            "alternate_mobile",
            "email",
            "loan_account_no",
            "imei_1",
            "imei_2",
            "created_at",
            'mobile_model',
            'total_emi_amount',
            'emi_per_month',
            'total_months',
            'paid_months',
            'remaining_months',
            'next_payment_date',
        ]
        read_only_fields = ["id", "created_at"]

# ---------------- PAYMENT SERIALIZER ----------------
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
