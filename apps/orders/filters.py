import django_filters

from .models import Order


class OrderFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=Order.Status.choices)
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = Order
        fields = ("status", "customer", "manager", "warehouse", "price_type", "currency")
