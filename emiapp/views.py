from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import Customer, EMI
from .serializers import CustomerSerializer, EMISerializer
from django.http import JsonResponse
from .models import Payment
from .serializers import PaymentSerializer
from rest_framework import generics, permissions
from .serializers import SignUpSerializer

def ping(request):
    return JsonResponse({"message": "pong"})

class SignUpView(generics.CreateAPIView):
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

class EMIViewSet(viewsets.ModelViewSet):
    queryset = EMI.objects.all()
    serializer_class = EMISerializer

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer