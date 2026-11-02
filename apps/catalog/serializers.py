from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import (
    MAX_SIZE,
    MIN_SIZE,
    Category,
    Color,
    ProductModel,
    SizeRun,
    Variant,
    validate_size_run,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name")


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ("id", "name", "hex_code")


class SizeRunSerializer(serializers.ModelSerializer):
    total_pairs = serializers.IntegerField(read_only=True)

    class Meta:
        model = SizeRun
        fields = ("id", "name", "sizes", "total_pairs")

    def validate_sizes(self, value):
        try:
            validate_size_run(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return {str(k): v for k, v in sorted(value.items(), key=lambda kv: int(kv[0]))}


class VariantSerializer(serializers.ModelSerializer):
    article = serializers.CharField(source="product_model.article", read_only=True)
    color_name = serializers.CharField(source="color.name", read_only=True)

    class Meta:
        model = Variant
        fields = (
            "id",
            "product_model",
            "article",
            "color",
            "color_name",
            "size",
            "barcode",
            "is_active",
        )
        read_only_fields = ("is_active",)


class ProductModelSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)
    season_display = serializers.CharField(source="get_season_display", read_only=True)

    class Meta:
        model = ProductModel
        fields = (
            "id",
            "article",
            "name",
            "category",
            "category_name",
            "gender",
            "gender_display",
            "season",
            "season_display",
            "description",
            "image",
            "default_size_run",
            "currency",
            "wholesale_price",
            "dealer_price",
            "retail_price",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("is_active",)

    def validate(self, attrs):
        prices = {
            key: attrs.get(key, getattr(self.instance, key, None))
            for key in ("wholesale_price", "dealer_price", "retail_price")
        }
        for key, value in prices.items():
            if value is not None and value < 0:
                raise serializers.ValidationError({key: "Narx manfiy bo'lishi mumkin emas."})
        return attrs


class ProductModelDetailSerializer(ProductModelSerializer):
    variants = VariantSerializer(many=True, read_only=True)

    class Meta(ProductModelSerializer.Meta):
        fields = (*ProductModelSerializer.Meta.fields, "variants")


class GenerateVariantsSerializer(serializers.Serializer):
    colors = serializers.PrimaryKeyRelatedField(queryset=Color.objects.all(), many=True)
    sizes = serializers.ListField(
        child=serializers.IntegerField(min_value=MIN_SIZE, max_value=MAX_SIZE),
        required=False,
        help_text="Berilmasa, modelning asosiy razmer qatori ishlatiladi.",
    )
    size_run = serializers.PrimaryKeyRelatedField(queryset=SizeRun.objects.all(), required=False)

    def validate(self, attrs):
        if not attrs["colors"]:
            raise serializers.ValidationError({"colors": "Kamida bitta rang tanlang."})

        if attrs.get("sizes"):
            return attrs
        size_run = attrs.get("size_run") or self.context["product_model"].default_size_run
        if size_run is None:
            raise serializers.ValidationError("Razmerlar ro'yxati yoki razmer qatorini ko'rsating.")
        attrs["sizes"] = size_run.size_list
        return attrs
