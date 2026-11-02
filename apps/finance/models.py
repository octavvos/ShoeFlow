from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.customers.models import Customer
from common.choices import Currency


class CurrencyRate(models.Model):
    """1 birlik valyutaning so'mdagi kursi (Markaziy bankdan yoki qo'lda kiritilgan)."""

    class Source(models.TextChoices):
        CBU = "cbu", "Markaziy bank"
        MANUAL = "manual", "Qo'lda"

    currency = models.CharField("valyuta", max_length=3, choices=Currency.choices)
    rate = models.DecimalField("kurs (so'm)", max_digits=14, decimal_places=4)
    date = models.DateField("sana")
    source = models.CharField("manba", max_length=10, choices=Source.choices, default=Source.MANUAL)

    class Meta:
        verbose_name = "valyuta kursi"
        verbose_name_plural = "valyuta kurslari"
        ordering = ("-date", "currency")
        constraints = [
            models.UniqueConstraint(fields=["currency", "date"], name="unique_rate_currency_date"),
        ]

    def __str__(self):
        return f"{self.date}: 1 {self.currency} = {self.rate} so'm"


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Naqd"
        CARD = "card", "Plastik karta"
        BANK = "bank", "Bank o'tkazmasi"
        CLICK = "click", "Click"
        PAYME = "payme", "Payme"

    customer = models.ForeignKey(
        Customer, verbose_name="mijoz", on_delete=models.PROTECT, related_name="payments"
    )
    order = models.ForeignKey(
        "orders.Order",
        verbose_name="buyurtma",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
    )
    amount = models.DecimalField(
        "summa", max_digits=16, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    currency = models.CharField("valyuta", max_length=3, choices=Currency.choices)
    method = models.CharField("to'lov usuli", max_length=10, choices=Method.choices)
    rate = models.DecimalField(
        "kurs",
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="To'lov valyutasi mijoz hisobi valyutasidan farq qilganda",
    )
    settlement_amount = models.DecimalField(
        "mijoz hisobidagi summa", max_digits=14, decimal_places=2
    )
    paid_at = models.DateField("to'lov sanasi", default=timezone.localdate)
    comment = models.TextField("izoh", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="qabul qilgan",
        on_delete=models.SET_NULL,
        null=True,
        related_name="+",
    )
    created_at = models.DateTimeField("yaratilgan", auto_now_add=True)
    is_cancelled = models.BooleanField("bekor qilingan", default=False)
    cancelled_at = models.DateTimeField("bekor qilingan sana", null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="bekor qilgan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    cancel_reason = models.TextField("bekor qilish sababi", blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "to'lov"
        verbose_name_plural = "to'lovlar"
        ordering = ("-paid_at", "-id")

    def __str__(self):
        return f"{self.customer}: {self.amount} {self.currency}"


class LedgerEntry(models.Model):
    """
    Mijoz hisobi jurnali (akt-sverka shu yerdan olinadi). Summa mijoz hisobi valyutasida:
    musbat — mijoz qarzi oshdi (jo'natish), manfiy — kamaydi (to'lov).
    Yozuvlar o'zgartirilmaydi; xato tuzatish uchun qarama-qarshi yozuv qo'shiladi.
    """

    class Type(models.TextChoices):
        OPENING = "opening", "Boshlang'ich qoldiq"
        SHIPMENT = "shipment", "Jo'natish"
        PAYMENT = "payment", "To'lov"
        PAYMENT_CANCEL = "payment_cancel", "To'lov bekor qilindi"
        ADJUSTMENT = "adjustment", "Tuzatish"

    customer = models.ForeignKey(
        Customer, verbose_name="mijoz", on_delete=models.PROTECT, related_name="ledger_entries"
    )
    type = models.CharField("turi", max_length=20, choices=Type.choices)
    amount = models.DecimalField("summa", max_digits=14, decimal_places=2)
    currency = models.CharField("valyuta", max_length=3, choices=Currency.choices)
    date = models.DateField("sana", default=timezone.localdate)
    description = models.CharField("tavsif", max_length=255, blank=True)
    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, null=True, blank=True, related_name="ledger_entries"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "hisob yozuvi"
        verbose_name_plural = "hisob yozuvlari"
        ordering = ("date", "id")
        indexes = [models.Index(fields=["customer", "date"])]

    def __str__(self):
        return f"{self.customer} {self.date} {self.amount:+}"
