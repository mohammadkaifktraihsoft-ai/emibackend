from rest_framework import serializers
from .models import Customer, EMI, Payment
from django.contrib.auth.models import User
from rest_framework import serializers

#--------------signup&login---------------
class SignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


# ---------------- EMISerializer ----------------
class EMISerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = EMI
        fields = '__all__'

# ---------------- CustomerSerializer ----------------
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

# ---------------- PaymentSerializer ----------------
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
