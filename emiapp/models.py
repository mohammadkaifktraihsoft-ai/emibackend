from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

# =========================
# USER PROFILE
# =========================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_image = models.ImageField(upload_to='profile/', null=True, blank=True)
    qr_image = models.ImageField(upload_to='qr/', null=True, blank=True)
    shop_name = models.CharField(max_length=255, blank=True)
    distributor_name = models.CharField(max_length=255, blank=True)
    distributor_contact = models.CharField(max_length=20, blank=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return self.user.username


# 🧩 Automatically create & update profile whenever a User is created or saved
@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
    else:
        instance.profile.save()


# =========================
# CUSTOMER
# =========================

class Customer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=100)
    mobile = models.CharField(max_length=15, unique=True)
    alternate_mobile = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    loan_account_no = models.CharField(max_length=50, blank=True, null=True)
    imei_1 = models.CharField(max_length=50, blank=True, null=True)
    imei_2 = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set on creation

    def __str__(self):
        return self.name


# =========================
# EMI
# =========================
class EMI(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="emis")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    next_due_date = models.DateField()
    is_closed = models.BooleanField(default=False)

    def __str__(self):
        return f"EMI for {self.customer.name}"


# =========================
# PAYMENT
# =========================
class Payment(models.Model):
    emi = models.ForeignKey(EMI, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_on = models.DateField(auto_now_add=True)
