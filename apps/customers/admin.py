from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import Contact, Customer, Interaction


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0


@admin.register(Customer)
class CustomerAdmin(SimpleHistoryAdmin):
    list_display = ("name", "type", "phone", "region", "manager", "credit_limit", "is_active")
    list_filter = ("type", "region", "is_active", "manager")
    search_fields = ("name", "phone", "inn")
    autocomplete_fields = ("manager",)
    inlines = (ContactInline,)


@admin.register(Interaction)
class InteractionAdmin(admin.ModelAdmin):
    list_display = ("customer", "type", "author", "occurred_at")
    list_filter = ("type",)
    search_fields = ("customer__name", "body")
    autocomplete_fields = ("customer",)
