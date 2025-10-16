from django.db import models

from django.contrib.auth.models import User
# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='profile/', null=True, blank=True)
    qr_image = models.ImageField(upload_to='qr/', null=True, blank=True)
    shop_name = models.CharField(max_length=255, blank=True)
    distributor_name = models.CharField(max_length=255, blank=True)
    distributor_contact = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.username

class Customer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, unique=True)
    email = models.EmailField(blank=True, null=True)

    def __str__(self):
        return self.name

class EMI(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="emis")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    next_due_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"EMI for {self.customer.name}"

# models.py
class Payment(models.Model):
    emi = models.ForeignKey(EMI, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_on = models.DateField(auto_now_add=True)
