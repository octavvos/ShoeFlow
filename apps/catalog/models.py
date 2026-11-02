from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords

from common.choices import Currency
from common.models import TimeStampedModel
from common.validators import ean13_check_digit, validate_ean13

MIN_SIZE = 15
MAX_SIZE = 50
size_validators = [MinValueValidator(MIN_SIZE), MaxValueValidator(MAX_SIZE)]

# Ichki shtrix-kodlar "2" bilan boshlanadi (GS1 bo'yicha do'kon ichidagi kodlar uchun ajratilgan)
INTERNAL_BARCODE_PREFIX = "200"


def validate_size_run(sizes: dict) -> None:
    """{"36": 1, "37": 2, ...} ko'rinishidagi razmer qatorini tekshiradi."""
    if not isinstance(sizes, dict) or not sizes:
        raise ValidationError("Razmer qatori bo'sh bo'lmagan lug'at bo'lishi kerak.")
    for size, qty in sizes.items():
        if not str(size).isdigit() or not MIN_SIZE <= int(size) <= MAX_SIZE:
            raise ValidationError(f"Noto'g'ri razmer: {size}.")
        if not isinstance(qty, int) or isinstance(qty, bool) or qty < 1:
            raise ValidationError(f"{size}-razmer uchun soni musbat butun son bo'lishi kerak.")


class Category(TimeStampedModel):
    name = models.CharField("nomi", max_length=100, unique=True)

    class Meta:
        verbose_name = "kategoriya"
        verbose_name_plural = "kategoriyalar"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField("nomi", max_length=50, unique=True)
    hex_code = models.CharField("HEX kod", max_length=7, blank=True)

    class Meta:
        verbose_name = "rang"
        verbose_name_plural = "ranglar"
        ordering = ("name",)

    def __str__(self):
        return self.name


class SizeRun(TimeStampedModel):
    """Razmer qatori (korobka): ulgurjida bir korobkada qaysi razmerdan nechta juft borligi."""

    name = models.CharField("nomi", max_length=100, unique=True)
    sizes = models.JSONField("razmerlar", validators=[validate_size_run])

    class Meta:
        verbose_name = "razmer qatori"
        verbose_name_plural = "razmer qatorlari"
        ordering = ("name",)

    def __str__(self):
        return self.name

    @property
    def total_pairs(self) -> int:
        return sum(self.sizes.values())

    @property
    def size_list(self) -> list[int]:
        return sorted(int(s) for s in self.sizes)


class ProductModel(TimeStampedModel):
    """Oyoq kiyim modeli (artikul). Har bir rang + razmer kombinatsiyasi — alohida Variant."""

    class Gender(models.TextChoices):
        MEN = "men", "Erkaklar"
        WOMEN = "women", "Ayollar"
        KIDS = "kids", "Bolalar"
        UNISEX = "unisex", "Uniseks"

    class Season(models.TextChoices):
        SUMMER = "summer", "Yozgi"
        WINTER = "winter", "Qishki"
        DEMI = "demi", "Bahor-kuz"
        ALL = "all", "Mavsumsiz"

    article = models.CharField("artikul", max_length=32, unique=True)
    name = models.CharField("nomi", max_length=255)
    category = models.ForeignKey(
        Category, verbose_name="kategoriya", on_delete=models.PROTECT, related_name="models"
    )
    gender = models.CharField("jins", max_length=10, choices=Gender.choices)
    season = models.CharField("mavsum", max_length=10, choices=Season.choices, default=Season.ALL)
    description = models.TextField("tavsif", blank=True)
    image = models.ImageField("rasm", upload_to="products/", blank=True)
    default_size_run = models.ForeignKey(
        SizeRun,
        verbose_name="asosiy razmer qatori",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    currency = models.CharField(
        "valyuta", max_length=3, choices=Currency.choices, default=Currency.USD
    )
    wholesale_price = models.DecimalField("ulgurji narx", max_digits=14, decimal_places=2)
    dealer_price = models.DecimalField("diler narxi", max_digits=14, decimal_places=2)
    retail_price = models.DecimalField("chakana narx", max_digits=14, decimal_places=2)
    is_active = models.BooleanField("faol", default=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "model"
        verbose_name_plural = "modellar"
        ordering = ("article",)

    def __str__(self):
        return f"{self.article} — {self.name}"


class Variant(TimeStampedModel):
    """SKU: model + rang + razmer. Omborda va buyurtmalarda aynan shu hisoblanadi."""

    product_model = models.ForeignKey(
        ProductModel, verbose_name="model", on_delete=models.CASCADE, related_name="variants"
    )
    color = models.ForeignKey(Color, verbose_name="rang", on_delete=models.PROTECT)
    size = models.PositiveSmallIntegerField("razmer", validators=size_validators)
    barcode = models.CharField(
        "shtrix-kod", max_length=13, unique=True, null=True, blank=True, validators=[validate_ean13]
    )
    is_active = models.BooleanField("faol", default=True)

    class Meta:
        verbose_name = "variant"
        verbose_name_plural = "variantlar"
        ordering = ("product_model__article", "color__name", "size")
        constraints = [
            models.UniqueConstraint(
                fields=["product_model", "color", "size"], name="unique_variant_model_color_size"
            ),
        ]

    def __str__(self):
        return f"{self.product_model.article} / {self.color} / {self.size}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Shtrix-kod berilmagan bo'lsa, id asosida ichki EAN-13 yaratiladi
        if not self.barcode:
            first12 = f"{INTERNAL_BARCODE_PREFIX}{self.pk:09d}"
            self.barcode = first12 + ean13_check_digit(first12)
            type(self).objects.filter(pk=self.pk).update(barcode=self.barcode)
