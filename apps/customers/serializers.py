from rest_framework import serializers

from apps.users.models import Role

from .models import Contact, Customer, Interaction
from .selectors import visible_customers


class VisibleCustomerMixin:
    def validate_customer(self, customer):
        # Boshqa menejerning mijoziga bog'lab bo'lmaydi
        if not visible_customers(self.context["request"].user).filter(pk=customer.pk).exists():
            raise serializers.ValidationError("Mijoz topilmadi.")
        return customer


class ContactSerializer(VisibleCustomerMixin, serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ("id", "customer", "full_name", "position", "phone", "telegram")


class InteractionSerializer(VisibleCustomerMixin, serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True, default=None)

    class Meta:
        model = Interaction
        fields = ("id", "customer", "type", "body", "occurred_at", "author", "author_name")
        read_only_fields = ("author",)


class CustomerSerializer(serializers.ModelSerializer):
    manager_name = serializers.CharField(
        source="manager.get_full_name", read_only=True, default=None
    )
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    region_display = serializers.CharField(source="get_region_display", read_only=True)

    class Meta:
        model = Customer
        fields = (
            "id",
            "name",
            "type",
            "type_display",
            "phone",
            "extra_phone",
            "region",
            "region_display",
            "address",
            "inn",
            "currency",
            "credit_limit",
            "manager",
            "manager_name",
            "tags",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("is_active",)

    def validate_manager(self, manager):
        if manager and manager.role != Role.SALES_MANAGER:
            raise serializers.ValidationError("Faqat savdo menejerini biriktirish mumkin.")
        return manager

    def validate_currency(self, value):
        customer = self.instance
        has_history = customer and (customer.orders.exists() or customer.ledger_entries.exists())
        if has_history and value != customer.currency:
            raise serializers.ValidationError(
                "Buyurtma yoki hisob-kitob bor mijozning valyutasini o'zgartirib bo'lmaydi."
            )
        return value

    def validate_credit_limit(self, value):
        if value < 0:
            raise serializers.ValidationError("Kredit limiti manfiy bo'lishi mumkin emas.")
        return value


class CustomerDetailSerializer(CustomerSerializer):
    contacts = ContactSerializer(many=True, read_only=True)

    class Meta(CustomerSerializer.Meta):
        fields = (*CustomerSerializer.Meta.fields, "contacts")
