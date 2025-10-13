from django.db import models

# Create your models here.
from django.db import models

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
