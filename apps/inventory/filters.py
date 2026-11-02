import django_filters

from .models import StockBalance, StockMovement


class StockBalanceFilter(django_filters.FilterSet):
    product_model = django_filters.NumberFilter(field_name="variant__product_model")
    color = django_filters.NumberFilter(field_name="variant__color")
    size = django_filters.NumberFilter(field_name="variant__size")
    available_lte = django_filters.NumberFilter(
        field_name="available_qty", lookup_expr="lte", label="mavjud soni ≤ (kam qolganlar)"
    )
    in_stock = django_filters.BooleanFilter(method="filter_in_stock", label="faqat bor bo'lganlar")

    class Meta:
        model = StockBalance
        fields = ("warehouse", "variant")

    def filter_in_stock(self, queryset, name, value):
        return queryset.filter(quantity__gt=0) if value else queryset.filter(quantity=0)


class StockMovementFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    product_model = django_filters.NumberFilter(field_name="variant__product_model")

    class Meta:
        model = StockMovement
        fields = ("warehouse", "variant", "type", "reference", "created_by")
