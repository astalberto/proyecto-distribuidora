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


class User(models.Model):
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)

    role = models.CharField(
        max_length=20,
        choices=Role.choices
    )

    distributor = models.ForeignKey(
        Distributor,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True
    )

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