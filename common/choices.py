from django.db import models


class Currency(models.TextChoices):
    UZS = "UZS", "So'm"
    USD = "USD", "AQSh dollari"


class Region(models.TextChoices):
    TASHKENT_CITY = "tashkent_city", "Toshkent shahri"
    TASHKENT = "tashkent", "Toshkent viloyati"
    ANDIJAN = "andijan", "Andijon"
    FERGANA = "fergana", "Farg'ona"
    NAMANGAN = "namangan", "Namangan"
    SAMARKAND = "samarkand", "Samarqand"
    BUKHARA = "bukhara", "Buxoro"
    NAVOI = "navoi", "Navoiy"
    KASHKADARYA = "kashkadarya", "Qashqadaryo"
    SURKHANDARYA = "surkhandarya", "Surxondaryo"
    JIZZAKH = "jizzakh", "Jizzax"
    SYRDARYA = "syrdarya", "Sirdaryo"
    KHOREZM = "khorezm", "Xorazm"
    KARAKALPAKSTAN = "karakalpakstan", "Qoraqalpog'iston Respublikasi"
