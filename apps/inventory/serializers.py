from rest_framework import serializers

from apps.catalog.models import Variant

from .models import StockBalance, StockMovement, Warehouse
from .services import StockLine


class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ("id", "name", "address", "is_active")
        read_only_fields = ("is_active",)


class StockBalanceSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    article = serializers.CharField(source="variant.product_model.article", read_only=True)
    model_name = serializers.CharField(source="variant.product_model.name", read_only=True)
    color = serializers.CharField(source="variant.color.name", read_only=True)
    size = serializers.IntegerField(source="variant.size", read_only=True)
    barcode = serializers.CharField(source="variant.barcode", read_only=True)
    available = serializers.IntegerField(source="available_qty", read_only=True)

    class Meta:
        model = StockBalance
        fields = (
            "id",
            "warehouse",
            "warehouse_name",
            "variant",
            "article",
            "model_name",
            "color",
            "size",
            "barcode",
            "quantity",
            "reserved",
            "available",
        )


class StockMovementSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    article = serializers.CharField(source="variant.product_model.article", read_only=True)
    color = serializers.CharField(source="variant.color.name", read_only=True)
    size = serializers.IntegerField(source="variant.size", read_only=True)
    created_by_name = serializers.CharField(
        source="created_by.get_full_name", read_only=True, default=None
    )

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "warehouse",
            "warehouse_name",
            "variant",
            "article",
            "color",
            "size",
            "type",
            "type_display",
            "quantity",
            "balance_after",
            "reference",
            "comment",
            "created_by",
            "created_by_name",
            "created_at",
        )


class StockLineSerializer(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(queryset=Variant.objects.all())
    quantity = serializers.IntegerField(min_value=1)

    def to_internal_value(self, data):
        attrs = super().to_internal_value(data)
        return StockLine(variant_id=attrs["variant"].id, quantity=attrs["quantity"])


def active_warehouse_field(**kwargs):
    return serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.filter(is_active=True), **kwargs
    )


class ReceiveSerializer(serializers.Serializer):
    warehouse = active_warehouse_field()
    items = StockLineSerializer(many=True, allow_empty=False)
    reference = serializers.CharField(required=False, allow_blank=True, max_length=50)
    comment = serializers.CharField(required=False, allow_blank=True)


class WriteOffSerializer(serializers.Serializer):
    warehouse = active_warehouse_field()
    items = StockLineSerializer(many=True, allow_empty=False)
    comment = serializers.CharField(help_text="Sabab: brak, yo'qotish va h.k.")


class TransferSerializer(serializers.Serializer):
    source = active_warehouse_field()
    target = active_warehouse_field()
    items = StockLineSerializer(many=True, allow_empty=False)
    comment = serializers.CharField(required=False, allow_blank=True)


class AdjustSerializer(serializers.Serializer):
    warehouse = active_warehouse_field()
    variant = serializers.PrimaryKeyRelatedField(queryset=Variant.objects.all())
    counted = serializers.IntegerField(min_value=0, help_text="Sanab chiqilgan juftlar soni")
    comment = serializers.CharField(required=False, allow_blank=True)
