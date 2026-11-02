from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.catalog.models import Variant
from common.models import TimeStampedModel


class Warehouse(TimeStampedModel):
    name = models.CharField("nomi", max_length=100, unique=True)
    address = models.TextField("manzil", blank=True)
    is_active = models.BooleanField("faol", default=True)

    class Meta:
        verbose_name = "ombor"
        verbose_name_plural = "omborlar"
        ordering = ("name",)

    def __str__(self):
        return self.name


class StockBalance(models.Model):
    """
    Ombordagi joriy qoldiq (juftlarda). Faqat services.py orqali, StockMovement bilan
    bir tranzaksiyada o'zgartiriladi. reserved — tasdiqlangan, lekin hali jo'natilmagan buyurtmalar.
    """

    warehouse = models.ForeignKey(
        Warehouse, verbose_name="ombor", on_delete=models.PROTECT, related_name="balances"
    )
    variant = models.ForeignKey(
        Variant, verbose_name="variant", on_delete=models.PROTECT, related_name="stock_balances"
    )
    quantity = models.PositiveIntegerField("qoldiq", default=0)
    reserved = models.PositiveIntegerField("rezervda", default=0)

    class Meta:
        verbose_name = "qoldiq"
        verbose_name_plural = "qoldiqlar"
        constraints = [
            models.UniqueConstraint(
                fields=["warehouse", "variant"], name="unique_balance_warehouse_variant"
            ),
            models.CheckConstraint(
                condition=Q(reserved__lte=F("quantity")), name="balance_reserved_lte_quantity"
            ),
        ]

    def __str__(self):
        return f"{self.warehouse} / {self.variant}: {self.quantity}"

    @property
    def available(self) -> int:
        return self.quantity - self.reserved


class StockMovement(models.Model):
    """Ombor harakatlari jurnali (ledger). Yozuvlar o'zgartirilmaydi va o'chirilmaydi."""

    class Type(models.TextChoices):
        RECEIPT = "receipt", "Kirim"
        SHIPMENT = "shipment", "Jo'natish"
        TRANSFER_OUT = "transfer_out", "Ko'chirish (chiqim)"
        TRANSFER_IN = "transfer_in", "Ko'chirish (kirim)"
        ADJUSTMENT = "adjustment", "Inventarizatsiya"
        WRITE_OFF = "write_off", "Hisobdan chiqarish"

    warehouse = models.ForeignKey(
        Warehouse, verbose_name="ombor", on_delete=models.PROTECT, related_name="movements"
    )
    variant = models.ForeignKey(
        Variant, verbose_name="variant", on_delete=models.PROTECT, related_name="movements"
    )
    type = models.CharField("turi", max_length=20, choices=Type.choices)
    quantity = models.IntegerField("soni", help_text="Kirim musbat, chiqim manfiy")
    balance_after = models.PositiveIntegerField("harakatdan keyingi qoldiq")
    reference = models.CharField("hujjat", max_length=50, blank=True)
    comment = models.TextField("izoh", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="kim", on_delete=models.SET_NULL, null=True
    )
    created_at = models.DateTimeField("sana", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "ombor harakati"
        verbose_name_plural = "ombor harakatlari"
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=["warehouse", "variant"])]

    def __str__(self):
        return f"{self.get_type_display()} {self.quantity:+d} — {self.variant}"
