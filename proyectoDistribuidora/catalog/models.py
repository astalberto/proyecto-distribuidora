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

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

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


class Category(models.Model):
    name = models.CharField(max_length=100)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="categories"
    )

    class Meta:
        verbose_name_plural = "Categories"
        constraints = [
            models.UniqueConstraint(
                fields=["distributor", "name"],
                name="unique_category_name_per_distributor"
            )
        ]

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="brands"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["distributor", "name"],
                name="unique_brand_name_per_distributor"
            )
        ]

    def __str__(self):
        return self.name


class Warehouse(models.Model):
    """Tier 4.5: a single row per distributor today, real model so a second
    warehouse later needs no further schema change to Product/Order/OrderItem."""
    name = models.CharField(max_length=100)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="warehouses"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["distributor", "name"],
                name="unique_warehouse_name_per_distributor"
            )
        ]

    def __str__(self):
        return self.name

    @classmethod
    def get_or_create_default(cls, distributor):
        """Single row per distributor today — centralizes the "which
        warehouse" question so callers (orders app, catalog stock
        management) never hardcode a lookup."""
        warehouse, _ = cls.objects.get_or_create(
            distributor=distributor,
            defaults={'name': 'Principal'},
        )
        return warehouse


class ProductStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    INACTIVE = "INACTIVE", "Inactivo"
    DISCONTINUED = "DISCONTINUED", "Descontinuado"


class UnitOfMeasure(models.TextChoices):
    PIECE = "PIECE", "Pieza"
    BOX = "BOX", "Caja"
    PACK = "PACK", "Paquete"
    BOTTLE = "BOTTLE", "Botella"
    KG = "KG", "Kilogramo"
    LITER = "LITER", "Litro"


class Product(models.Model):
    name = models.CharField(max_length=255)

    # DR-05/DR-06 era fields
    description = models.TextField(blank=True)

    # IVA-exclusive (Tier 4.5 resolution) — Ecuador's 15% IVA is calculated
    # on top wherever a final charged amount is shown, never baked in here.
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Tier 4.5: replaces the DR-06 `is_active` boolean outright. Migration
    # 0005 maps is_active=True -> ACTIVE, is_active=False -> INACTIVE.
    # DISCONTINUED is a distinct explicit action, never auto-mapped.
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE
    )

    # DR-05: alert threshold per product, configurable by distributor (US-25)
    low_stock_threshold = models.PositiveIntegerField(default=5)

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="products"
    )

    # Tier 4.5 additions
    sku = models.CharField(max_length=64)

    # Free text, no EAN-13/UPC validation (Tier 4.5 resolution) — Ecuadorian
    # retail mixes real GS1 barcodes with internally-assigned codes for
    # repackaged/bulk goods; blank when the product has no scannable code.
    barcode = models.CharField(max_length=64, blank=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    brand = models.ForeignKey(
        Brand,
        on_delete=models.PROTECT,
        related_name="products"
    )

    unit_of_measure = models.CharField(
        max_length=20,
        choices=UnitOfMeasure.choices,
        default=UnitOfMeasure.PIECE
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["distributor", "sku"],
                name="unique_product_sku_per_distributor"
            )
        ]

    def __str__(self):
        return self.name

    def total_stock(self):
        """Sum of StockLevel quantities across all warehouses. Call sites
        that iterate many products should prefetch_related('stock_levels')
        first to avoid one query per product."""
        return sum(sl.quantity for sl in self.stock_levels.all())

    def is_out_of_stock(self):
        return self.total_stock() == 0

    def active_discount(self):
        """Returns the currently-active Discount, if any. Expects callers
        that iterate many products to prefetch_related('discounts') first —
        this filters the already-fetched list in Python rather than issuing
        a new query per product (avoids the N+1 class Tier 3 already fixed
        once for FK joins)."""
        from django.utils import timezone
        today = timezone.now().date()
        for discount in self.discounts.all():
            if discount.start_date <= today <= discount.end_date:
                return discount
        return None

    def current_price(self):
        """unit_price with the active discount applied, if any. Never
        stored — expiry needs no cleanup job. Clamped at zero."""
        discount = self.active_discount()
        if discount is None:
            return self.unit_price
        return discount.apply_to(self.unit_price)


class DiscountType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "Porcentaje"
    FIXED_AMOUNT = "FIXED_AMOUNT", "Monto fijo"


class Discount(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="discounts"
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices
    )

    discount_value = models.DecimalField(max_digits=10, decimal_places=2)

    start_date = models.DateField()

    end_date = models.DateField()

    def apply_to(self, price):
        """Compute the discounted price, clamped at zero. Percentage math is
        computed against the clean (IVA-exclusive) base price."""
        if self.discount_type == DiscountType.PERCENTAGE:
            discounted = price * (1 - (self.discount_value / 100))
        else:
            discounted = price - self.discount_value
        return max(discounted, 0)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError('La fecha de fin no puede ser anterior a la fecha de inicio.')
        # Stacking rule: at most one active discount per product — checked at
        # the Python/form layer rather than a DB exclusion constraint, since
        # this project runs on SQLite in dev (no native date-range overlap
        # constraint support).
        if self.product_id:
            overlapping = Discount.objects.filter(product_id=self.product_id).exclude(pk=self.pk)
            for other in overlapping:
                if self.start_date <= other.end_date and other.start_date <= self.end_date:
                    raise ValidationError(
                        'Ya existe un descuento activo para este producto en ese rango de fechas.'
                    )

    def __str__(self):
        return f"{self.product} — {self.get_discount_type_display()} {self.discount_value}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = models.ImageField(upload_to="products/")

    is_main = models.BooleanField(default=False)

    def __str__(self):
        return f"{'Principal' if self.is_main else 'Adicional'} — {self.product}"


class StockLevel(models.Model):
    """Tier 4.5: replaces VendorInventory as the source of truth for stock,
    both for catalog display and for orders/views.py's aceptar_pedido lock.
    Centralized (not per-vendor) — confirmed with the business 2026-07-21."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="stock_levels"
    )

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stock_levels"
    )

    quantity = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "warehouse"],
                name="unique_product_warehouse"
            )
        ]

    def __str__(self):
        return f"{self.product} @ {self.warehouse} - {self.quantity}"
