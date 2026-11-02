from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import CurrencyRate, LedgerEntry, Payment


@admin.register(CurrencyRate)
class CurrencyRateAdmin(admin.ModelAdmin):
    list_display = ("date", "currency", "rate", "source")
    list_filter = ("currency", "source")
    date_hierarchy = "date"


class ReadOnlyAdmin(admin.ModelAdmin):
    """Pul yozuvlari faqat API (services.py) orqali yaratiladi, admin'da faqat ko'riladi."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin, SimpleHistoryAdmin):
    list_display = ("paid_at", "customer", "amount", "currency", "method", "is_cancelled")
    list_filter = ("method", "currency", "is_cancelled")
    search_fields = ("customer__name",)
    list_select_related = ("customer",)
    date_hierarchy = "paid_at"


@admin.register(LedgerEntry)
class LedgerEntryAdmin(ReadOnlyAdmin):
    list_display = ("date", "customer", "type", "amount", "currency", "description")
    list_filter = ("type", "currency")
    search_fields = ("customer__name", "description")
    list_select_related = ("customer",)
    date_hierarchy = "date"
