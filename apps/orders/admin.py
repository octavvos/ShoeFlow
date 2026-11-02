from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ("variant", "quantity", "price")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(SimpleHistoryAdmin):
    """
    Faqat ko'rish uchun: buyurtma holati va qatorlari ombor rezervi bilan bog'liq,
    shuning uchun ular faqat API (services.py) orqali o'zgaradi.
    """

    list_display = (
        "number",
        "customer",
        "manager",
        "status",
        "total_amount",
        "currency",
        "created_at",
    )
    list_filter = ("status", "warehouse", "manager")
    search_fields = ("customer__name",)
    list_select_related = ("customer", "manager")
    inlines = (OrderItemInline,)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
