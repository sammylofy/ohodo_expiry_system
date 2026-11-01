from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Product(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    batch_number = models.CharField(max_length=100, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    manufacturing_date = models.DateField()
    expiry_date = models.DateField()
    cost_price = models.DecimalField(max_digits=12, decimal_places=2)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['expiry_date', 'name']

    def __str__(self):
        return f"{self.name} [Batch: {self.batch_number}]"

    @property
    def days_to_expiry(self):
        today = timezone.localdate()
        return (self.expiry_date - today).days

    @property
    def status(self):
        days = self.days_to_expiry
        if days < 0:
            return "Expired"
        elif days <= 7:
            return "Critical"
        elif days <= 30:
            return "Warning"
        return "Safe"

    @property
    def status_badge_class(self):
        status = self.status
        if status == "Expired":
            return "bg-danger"
        elif status == "Critical":
            return "bg-warning text-dark"
        elif status == "Warning":
            return "bg-info text-dark"
        return "bg-success"

    @property
    def profit_margin(self):
        return self.selling_price - self.cost_price


class AlertLog(models.Model):
    ALERT_TYPES = (
        ('Email', 'Email'),
        ('SMS', 'SMS'),
        ('WhatsApp', 'WhatsApp'),
    )
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    message = models.TextField()
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.alert_type} - {self.product.name} ({self.status})"


class StoreProfile(models.Model):
    store_name = models.CharField(max_length=200, default="Ohodo Retail Store")
    owner_email = models.EmailField(default="owner@ohodostore.com")
    owner_phone = models.CharField(
        max_length=20,
        default="2348000000000",
        help_text="Format: 234xxxxxxxxxx (e.g., 2348031234567)"
    )
    address = models.TextField(default="Along Enugu-Nsukka Express Road, Ohodo, Igbo-Etiti LGA, Enugu State")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Store Profile"
        verbose_name_plural = "Store Profile"

    def save(self, *args, **kwargs):
        # Enforce Singleton pattern: always use pk=1
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.store_name


class Sale(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sales')
    quantity_sold = models.PositiveIntegerField()
    sold_at = models.DateTimeField(auto_now_add=True)
    sold_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-sold_at']

    @property
    def total_amount(self):
        return self.quantity_sold * self.product.selling_price

    def __str__(self):
        return f"{self.product.name} x {self.quantity_sold}"