from django.db import models
from django.contrib.auth.models import AbstractUser


class Role(models.TextChoices):
    DISTRIBUTOR = "DISTRIBUTOR", "Distributor"
    STORE_OWNER = "STORE_OWNER", "Store Owner"
    VENDOR = "VENDOR", "Vendor"
    DELIVERY = "DELIVERY", "Delivery"


class Distributor(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    # username is kept from AbstractUser but made optional since we log in with email
    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        blank=True
    )

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # email is already USERNAME_FIELD, no extra required fields

    def __str__(self):
        return self.email


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens"
    )

    token = models.CharField(max_length=255, unique=True)

    expires_at = models.DateTimeField()

    used_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return self.token


class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    # String FK avoids circular import with the orders app
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications"
    )

    message = models.CharField(max_length=500)

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} — {self.message[:50]}"