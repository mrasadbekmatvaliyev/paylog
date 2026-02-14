from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone, password=None, **extra_fields):
        if not phone:
            raise ValueError("The phone number must be set")
        user = self.model(phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    phone = models.CharField(max_length=20, unique=True)
    telegram_user_id = models.CharField(max_length=32, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    default_currency = models.ForeignKey(
        "finance.Currency",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
    )

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.phone

    def save(self, *args, **kwargs):
        if self.default_currency_id is None:
            try:
                from finance.models import Currency

                currency, _ = Currency.objects.get_or_create(
                    code="UZS",
                    defaults={"name": "Uzbekistani Som", "is_active": True},
                )
                if not currency.is_active:
                    currency.is_active = True
                    currency.save(update_fields=["is_active"])
                self.default_currency = currency
            except (OperationalError, ProgrammingError):
                # During early migrations, finance tables may not exist yet.
                pass
        super().save(*args, **kwargs)


class OTP(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=5)
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["phone", "is_used", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.phone} - {self.code}"


class TelegramOTP(models.Model):
    telegram_user_id = models.CharField(max_length=32)
    code = models.CharField(max_length=5)
    attempts = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["telegram_user_id", "is_used", "expires_at"]),
            models.Index(fields=["code", "is_used", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.telegram_user_id} - {self.code}"
