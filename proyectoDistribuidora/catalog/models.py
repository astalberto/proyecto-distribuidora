from django.db import models
from accounts.models import Distributor, User


class Store(models.Model):
    name = models.CharField(max_length=255)
    
    address = models.CharField(
        max_length=255,
        blank=True
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True
    )
    
    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="stores"
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="stores"
    )

    # DR-01: vendor assigned by distributor; auto-populates Order.vendor at order creation
    vendor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_stores"
    )

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # DR-06: soft-delete; deactivated products hidden from order flow
    is_active = models.BooleanField(default=True)

    # DR-05: alert threshold per product, configurable by distributor (US-25)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="products"
    )

    def __str__(self):
        return self.name


class VendorInventory(models.Model):
    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="inventory"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="inventory"
    )

    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["vendor", "product"],
                name="unique_vendor_product"
            )
        ]

    def __str__(self):
        return f"{self.vendor} - {self.product}"