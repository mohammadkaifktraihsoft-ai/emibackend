from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import Customer, EMI
from .serializers import CustomerSerializer, EMISerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

class EMIViewSet(viewsets.ModelViewSet):
    queryset = EMI.objects.all()
    serializer_class = EMISerializer
