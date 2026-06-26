from django.db import models
from django.utils import timezone

from accounts.models import User
from orders.models import Order


class DeliveryConfirmation(models.Model):
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="delivery_confirmation"
    )

    delivery_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="deliveries"
    )

    photo_public_id = models.CharField(max_length=255)

    confirmed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Delivery for Order {self.order.id}"