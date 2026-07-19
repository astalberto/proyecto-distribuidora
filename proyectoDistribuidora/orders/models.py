from django.db import models

from accounts.models import User
from catalog.models import Store, Product


class OrderStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Rejected"
    DISPATCHED = "DISPATCHED", "Dispatched"
    # DELIVERED is non-terminal: it means "delivery person dropped it off,
    # awaiting store owner confirmation" (DR-09). The store owner then moves
    # it to CONFIRMED (received as expected) or DELIVERY_ISSUE (dispute);
    # resolving an issue moves it back to CONFIRMED.
    DELIVERED = "DELIVERED", "Delivered"
    DELIVERY_ISSUE = "DELIVERY_ISSUE", "Delivery Issue"
    CONFIRMED = "CONFIRMED", "Confirmed"


class Order(models.Model):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )

    previous_order = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resubmissions"
    )

    # Set by vendor on rejection; surfaced in store owner notification (US-12)
    rejection_reason = models.CharField(max_length=500, blank=True)

    # DR-09: store owner's delivery-issue report and the vendor's resolution.
    # No structured remediation (inventory adjustment, partial fulfillment)
    # yet — notes only; see docs/requirements.md.
    issue_description = models.TextField(blank=True)
    issue_reported_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # NFR-02.6: composite index for the vendor's pending-orders queries
        # and the polling endpoint; a separate index for store-scoped
        # lookups (store owner's order list, distributor dashboard).
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['store']),
        ]

    def __str__(self):
        return f"Order {self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    unit_price_at_time = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"],
                name="unique_order_product"
            )
        ]

    def __str__(self):
        return f"{self.product} ({self.quantity})"