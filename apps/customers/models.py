from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

from common.choices import Currency, Region
from common.models import TimeStampedModel
from common.validators import inn_validator, phone_validator


class Customer(TimeStampedModel):
    class Type(models.TextChoices):
        DEALER = "dealer", "Diler"
        WHOLESALE = "wholesale", "Ulgurji do'kon"
        RETAIL = "retail", "Chakana"
        MARKETPLACE = "marketplace", "Marketpleys"

    name = models.CharField("nomi", max_length=255)
    type = models.CharField("turi", max_length=20, choices=Type.choices, default=Type.WHOLESALE)
    phone = models.CharField("telefon", max_length=13, validators=[phone_validator])
    extra_phone = models.CharField(
        "qo'shimcha telefon", max_length=13, blank=True, validators=[phone_validator]
    )
    region = models.CharField("viloyat", max_length=20, choices=Region.choices)
    address = models.TextField("manzil", blank=True)
    inn = models.CharField("STIR (INN)", max_length=9, blank=True, validators=[inn_validator])
    currency = models.CharField(
        "hisob-kitob valyutasi", max_length=3, choices=Currency.choices, default=Currency.USD
    )
    credit_limit = models.DecimalField("kredit limiti", max_digits=14, decimal_places=2, default=0)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="mas'ul menejer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
    )
    tags = ArrayField(
        models.CharField(max_length=50), verbose_name="teglar", default=list, blank=True
    )
    notes = models.TextField("izoh", blank=True)
    is_active = models.BooleanField("faol", default=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "mijoz"
        verbose_name_plural = "mijozlar"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=["inn"], condition=~Q(inn=""), name="unique_customer_inn"
            ),
        ]
        indexes = [models.Index(fields=["phone"])]

    def __str__(self):
        return self.name


class Contact(TimeStampedModel):
    customer = models.ForeignKey(
        Customer, verbose_name="mijoz", on_delete=models.CASCADE, related_name="contacts"
    )
    full_name = models.CharField("F.I.Sh.", max_length=255)
    position = models.CharField("lavozimi", max_length=100, blank=True)
    phone = models.CharField("telefon", max_length=13, validators=[phone_validator])
    telegram = models.CharField("Telegram", max_length=64, blank=True)

    class Meta:
        verbose_name = "kontakt shaxs"
        verbose_name_plural = "kontakt shaxslar"
        ordering = ("full_name",)

    def __str__(self):
        return self.full_name


class Interaction(TimeStampedModel):
    """Mijoz bilan bo'lgan muloqot: qo'ng'iroq, uchrashuv, xabar yoki izoh."""

    class Type(models.TextChoices):
        CALL = "call", "Qo'ng'iroq"
        MEETING = "meeting", "Uchrashuv"
        MESSAGE = "message", "Xabar"
        NOTE = "note", "Izoh"

    customer = models.ForeignKey(
        Customer, verbose_name="mijoz", on_delete=models.CASCADE, related_name="interactions"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="muallif", on_delete=models.SET_NULL, null=True
    )
    type = models.CharField("turi", max_length=20, choices=Type.choices)
    body = models.TextField("mazmuni")
    occurred_at = models.DateTimeField("sana", default=timezone.now)

    class Meta:
        verbose_name = "muloqot"
        verbose_name_plural = "muloqotlar"
        ordering = ("-occurred_at",)

    def __str__(self):
        return f"{self.get_type_display()} — {self.customer}"
