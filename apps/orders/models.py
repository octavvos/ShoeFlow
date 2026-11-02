from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from apps.catalog.models import Variant
from apps.customers.models import Customer
from apps.inventory.models import Warehouse
from common.choices import Currency
from common.models import TimeStampedModel


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Qoralama"
        CONFIRMED = "confirmed", "Tasdiqlangan"
        SHIPPED = "shipped", "Jo'natilgan"
        DELIVERED = "delivered", "Yetkazilgan"
        CANCELLED = "cancelled", "Bekor qilingan"

    class PriceType(models.TextChoices):
        WHOLESALE = "wholesale", "Ulgurji"
        DEALER = "dealer", "Diler"
        RETAIL = "retail", "Chakana"

    customer = models.ForeignKey(
        Customer, verbose_name="mijoz", on_delete=models.PROTECT, related_name="orders"
    )
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="menejer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    warehouse = models.ForeignKey(
        Warehouse, verbose_name="jo'natish ombori", on_delete=models.PROTECT, related_name="orders"
    )
    status = models.CharField(
        "holati", max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    price_type = models.CharField("narx turi", max_length=20, choices=PriceType.choices)
    currency = models.CharField("valyuta", max_length=3, choices=Currency.choices)
    discount_percent = models.DecimalField(
        "chegirma (%)",
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    total_amount = models.DecimalField(
        "jami summa", max_digits=14, decimal_places=2, default=0, help_text="Chegirma bilan"
    )
    comment = models.TextField("izoh", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="yaratgan",
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    confirmed_at = models.DateTimeField("tasdiqlangan sana", null=True, blank=True)
    shipped_at = models.DateTimeField("jo'natilgan sana", null=True, blank=True)
    delivered_at = models.DateTimeField("yetkazilgan sana", null=True, blank=True)
    cancelled_at = models.DateTimeField("bekor qilingan sana", null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "buyurtma"
        verbose_name_plural = "buyurtmalar"
        ordering = ("-created_at", "-id")

    def __str__(self):
        return f"{self.number} — {self.customer}"

    @property
    def number(self) -> str:
        return f"Z-{self.pk:06d}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, verbose_name="buyurtma", on_delete=models.CASCADE, related_name="items"
    )
    variant = models.ForeignKey(Variant, verbose_name="variant", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField("soni (juft)", validators=[MinValueValidator(1)])
    price = models.DecimalField("narxi (1 juft)", max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = "buyurtma qatori"
        verbose_name_plural = "buyurtma qatorlari"
        ordering = ("variant__product_model__article", "variant__color__name", "variant__size")
        constraints = [
            models.UniqueConstraint(fields=["order", "variant"], name="unique_order_variant"),
        ]

    def __str__(self):
        return f"{self.variant} × {self.quantity}"

    @property
    def amount(self):
        return self.quantity * self.price
