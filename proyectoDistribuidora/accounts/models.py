import secrets

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class Role(models.TextChoices):
    DISTRIBUTOR = "DISTRIBUTOR", "Distributor"
    STORE_OWNER = "STORE_OWNER", "Store Owner"
    VENDOR = "VENDOR", "Vendor"
    DELIVERY = "DELIVERY", "Delivery"


class Distributor(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)

    # Opaque per-distributor invite token: powers the STORE_OWNER
    # self-registration link/QR code. Deliberately not a public distributor
    # picker — the token itself implies which distributor a new store owner
    # is joining, so the list of distributors is never exposed.
    invite_token = models.CharField(max_length=64, unique=True, editable=False)

    def save(self, *args, **kwargs):
        if not self.invite_token:
            self.invite_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def regenerate_invite_token(self):
        """Revoke the current invite link (e.g. after it leaks) and issue a new one."""
        self.invite_token = secrets.token_urlsafe(32)
        self.save(update_fields=['invite_token'])

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


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

    objects = UserManager()

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