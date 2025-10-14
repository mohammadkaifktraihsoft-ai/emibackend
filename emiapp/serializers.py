from rest_framework import serializers
from .models import Customer, EMI

class EMISerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = EMI
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    emis = EMISerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = '__all__'

# serializers.py
from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
