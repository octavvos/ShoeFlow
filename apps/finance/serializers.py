from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.customers.selectors import visible_customers
from apps.orders.models import Order
from common.choices import Currency

from .models import CurrencyRate, LedgerEntry, Payment


@extend_schema_field(OpenApiTypes.INT)
class VisibleCustomerField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        return visible_customers(self.context["request"].user)


class CurrencyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRate
        fields = ("id", "currency", "rate", "date", "source")
        read_only_fields = ("source",)

    def validate_currency(self, value):
        if value == Currency.UZS:
            raise serializers.ValidationError("So'm uchun kurs kiritilmaydi.")
        return value

    def validate_rate(self, value):
        if value <= 0:
            raise serializers.ValidationError("Kurs musbat bo'lishi kerak.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    number = serializers.SerializerMethodField()
    customer = VisibleCustomerField()
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    order = serializers.PrimaryKeyRelatedField(
        queryset=Order.objects.all(), required=False, allow_null=True
    )
    method_display = serializers.CharField(source="get_method_display", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = Payment
        fields = (
            "id",
            "number",
            "customer",
            "customer_name",
            "order",
            "amount",
            "currency",
            "method",
            "method_display",
            "rate",
            "settlement_amount",
            "paid_at",
            "comment",
            "created_by",
            "created_by_name",
            "created_at",
            "is_cancelled",
            "cancelled_at",
            "cancel_reason",
        )
        read_only_fields = (
            "settlement_amount",
            "created_by",
            "is_cancelled",
            "cancelled_at",
            "cancel_reason",
        )
        extra_kwargs = {
            "rate": {"help_text": "Berilmasa, to'lov sanasidagi so'nggi kurs olinadi"},
        }

    def get_number(self, obj) -> str:
        return f"T-{obj.pk:06d}"

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Summa musbat bo'lishi kerak.")
        return value


class CancelPaymentSerializer(serializers.Serializer):
    reason = serializers.CharField()


class LedgerEntrySerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    customer_name = serializers.CharField(source="customer.name", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = (
            "id",
            "customer",
            "customer_name",
            "type",
            "type_display",
            "amount",
            "currency",
            "date",
            "description",
            "order",
            "payment",
            "created_at",
        )


class AdjustmentSerializer(serializers.Serializer):
    customer = VisibleCustomerField()
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Musbat — mijoz qarzi oshadi, manfiy — kamayadi",
    )
    description = serializers.CharField(max_length=255)
    date = serializers.DateField(required=False)
    opening = serializers.BooleanField(default=False, help_text="Boshlang'ich qoldiqmi")


class CustomerBalanceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    manager = serializers.IntegerField(source="manager_id", allow_null=True)
    manager_name = serializers.CharField(source="manager.get_full_name", default=None)
    currency = serializers.CharField()
    credit_limit = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance = serializers.DecimalField(
        max_digits=14, decimal_places=2, help_text="Musbat — qarz, manfiy — oldindan to'lov"
    )
    open_orders_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, help_text="Tasdiqlangan, hali jo'natilmagan buyurtmalar"
    )
    available_credit = serializers.DecimalField(max_digits=14, decimal_places=2)
    last_payment_date = serializers.DateField(allow_null=True)


class ReconciliationQuerySerializer(serializers.Serializer):
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    export = serializers.ChoiceField(choices=["xlsx"], required=False)


class ReconciliationRowSerializer(serializers.Serializer):
    date = serializers.DateField()
    type = serializers.CharField()
    type_display = serializers.CharField()
    reference = serializers.CharField()
    description = serializers.CharField()
    debit = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit = serializers.DecimalField(max_digits=14, decimal_places=2)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2)


class ReconciliationSerializer(serializers.Serializer):
    customer = serializers.IntegerField(source="customer.id")
    customer_name = serializers.CharField(source="customer.name")
    currency = serializers.CharField()
    date_from = serializers.DateField()
    date_to = serializers.DateField()
    opening_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    debit_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    credit_total = serializers.DecimalField(max_digits=14, decimal_places=2)
    closing_balance = serializers.DecimalField(max_digits=14, decimal_places=2)
    rows = ReconciliationRowSerializer(many=True)
