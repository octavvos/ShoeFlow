from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from common.validators import phone_validator


class Role(models.TextChoices):
    ADMIN = "admin", "Administrator"
    DIRECTOR = "director", "Direktor"
    SALES_MANAGER = "sales_manager", "Savdo menejeri"
    PRODUCTION_HEAD = "production_head", "Ishlab chiqarish boshlig'i"
    WAREHOUSE = "warehouse", "Omborchi"
    ACCOUNTANT = "accountant", "Hisobchi"
    WORKER = "worker", "Ishchi"


MANAGEMENT_ROLES = frozenset({Role.ADMIN, Role.DIRECTOR})


class KosibchiUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    role = models.CharField("rol", max_length=32, choices=Role.choices, default=Role.WORKER)
    phone = models.CharField("telefon", max_length=13, blank=True, validators=[phone_validator])
    telegram_id = models.BigIntegerField("Telegram ID", null=True, blank=True, unique=True)

    objects = KosibchiUserManager()

    class Meta:
        verbose_name = "foydalanuvchi"
        verbose_name_plural = "foydalanuvchilar"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_management(self) -> bool:
        return self.is_superuser or self.role in MANAGEMENT_ROLES
