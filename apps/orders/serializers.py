from rest_framework import serializers

from apps.catalog.models import Color, ProductModel, SizeRun, Variant
from apps.customers.selectors import visible_customers
from apps.inventory.serializers import active_warehouse_field

from . import services
from .models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    article = serializers.CharField(source="variant.product_model.article", read_only=True)
    model_name = serializers.CharField(source="variant.product_model.name", read_only=True)
    color = serializers.CharField(source="variant.color.name", read_only=True)
    size = serializers.IntegerField(source="variant.size", read_only=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "variant",
            "article",
            "model_name",
            "color",
            "size",
            "quantity",
            "price",
            "amount",
        )


class VisibleCustomerField(serializers.PrimaryKeyRelatedField):
    def get_queryset(self):
        return visible_customers(self.context["request"].user).filter(is_active=True)


class OrderSerializer(serializers.ModelSerializer):
    number = serializers.CharField(read_only=True)
    customer = VisibleCustomerField()
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    manager_name = serializers.CharField(
        source="manager.get_full_name", read_only=True, default=None
    )
    warehouse = active_warehouse_field()
    warehouse_name = serializers.CharField(source="warehouse.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    price_type = serializers.ChoiceField(
        choices=Order.PriceType.choices,
        required=False,
        help_text="Berilmasa, mijoz turidan aniqlanadi",
    )
    total_pairs = serializers.IntegerField(read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "number",
            "customer",
            "customer_name",
            "manager",
            "manager_name",
            "warehouse",
            "warehouse_name",
            "status",
            "status_display",
            "price_type",
            "currency",
            "discount_percent",
            "total_amount",
            "total_pairs",
            "comment",
            "confirmed_at",
            "shipped_at",
            "delivered_at",
            "cancelled_at",
            "created_at",
        )
        read_only_fields = (
            "manager",
            "status",
            "currency",
            "total_amount",
            "confirmed_at",
            "shipped_at",
            "delivered_at",
            "cancelled_at",
        )

    def get_fields(self):
        fields = super().get_fields()
        # Mijoz va narx turi faqat yaratishda beriladi
        if self.instance is not None:
            fields["customer"].read_only = True
            fields["price_type"].read_only = True
        return fields

    def create(self, validated_data):
        return services.create_order(user=self.context["request"].user, **validated_data)

    def update(self, instance, validated_data):
        return services.update_order(instance, user=self.context["request"].user, **validated_data)


class OrderDetailSerializer(OrderSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = (*OrderSerializer.Meta.fields, "items")


class AddItemSerializer(serializers.Serializer):
    variant = serializers.PrimaryKeyRelatedField(
        queryset=Variant.objects.select_related("product_model")
    )
    quantity = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0,
        required=False,
        help_text="Berilmasa, katalogdagi narx olinadi",
    )


class AddBoxesSerializer(serializers.Serializer):
    product_model = serializers.PrimaryKeyRelatedField(queryset=ProductModel.objects.all())
    color = serializers.PrimaryKeyRelatedField(queryset=Color.objects.all())
    size_run = serializers.PrimaryKeyRelatedField(
        queryset=SizeRun.objects.all(),
        required=False,
        help_text="Berilmasa, modelning asosiy razmer qatori olinadi",
    )
    count = serializers.IntegerField(min_value=1, help_text="Korobkalar soni")

    def validate(self, attrs):
        attrs.setdefault("size_run", attrs["product_model"].default_size_run)
        if attrs["size_run"] is None:
            raise serializers.ValidationError({"size_run": "Razmer qatorini ko'rsating."})
        return attrs


class UpdateItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1, required=False)
    price = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=0, required=False)
