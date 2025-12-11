from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

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
    mobile_model = models.CharField(max_length=255, null=True, blank=True)
    total_emi_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    emi_per_month = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_months = models.IntegerField(null=True, blank=True)
    paid_months = models.IntegerField(default=0)
    remaining_months = models.IntegerField(null=True, blank=True)    
    next_payment_date = models.DateField(null=True, blank=True)


    def __str__(self):
        return self.name

#==========================
#lock/unlock device status
#=========================

class Device(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="devices")
    customer = models.ForeignKey("Customer", on_delete=models.SET_NULL, null=True, blank=True, related_name="device")
    imei = models.CharField(max_length=50, unique=True)
    is_locked = models.BooleanField(default=False)
    registered_at = models.DateTimeField(auto_now_add=True)
    last_action = models.CharField(max_length=20, blank=True, null=True)  # "locked" / "unlocked" / "registered"
    last_updated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        status = "🔒 Locked" if self.is_locked else "🔓 Unlocked"
        return f"{self.customer.name if self.customer else 'Unassigned'} ({status})"


#======= blance key =================

class BalanceKey(models.Model):
    key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="balance_keys")
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey(
        'Customer', null=True, blank=True, on_delete=models.SET_NULL, related_name='used_key'
    )
    qr_image = models.ImageField(upload_to='balance_qr/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    used_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save first to get ID

        # ✅ Automatically generate QR code after saving (only once)
        if not self.qr_image:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(str(self.key))
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            file_name = f'balancekey_{self.key}.png'
            self.qr_image.save(file_name, ContentFile(buffer.getvalue()), save=False)
            super().save(update_fields=['qr_image'])  # Save again with QR image

    def __str__(self):
        return f"{self.key} ({'USED' if self.is_used else 'AVAILABLE'})"

#========================

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


# ========================
# FMC
# ========================
class FCM(models.Model):
    imei_1 = models.CharField(max_length=255, unique=True)  # IMEI or random ID
    fcm_token = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.imei_1