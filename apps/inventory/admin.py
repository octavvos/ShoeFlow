from django.contrib import admin

from .models import StockBalance, StockMovement, Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "is_active")
    search_fields = ("name",)


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    """Qoldiqlar faqat ko'rish uchun — o'zgartirish faqat ombor harakatlari orqali."""

    list_display = ("warehouse", "variant", "quantity", "reserved")
    list_filter = ("warehouse",)
    search_fields = ("variant__product_model__article", "variant__barcode")
    list_select_related = ("warehouse", "variant__product_model", "variant__color")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockMovement)
class StockMovementAdmin(StockBalanceAdmin):
    list_display = (
        "created_at",
        "warehouse",
        "variant",
        "type",
        "quantity",
        "balance_after",
        "reference",
    )
    list_filter = ("warehouse", "type")
    search_fields = ("variant__product_model__article", "variant__barcode", "reference")
