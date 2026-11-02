import django_filters
from django.db.models import F

from apps.customers.models import Customer

from .models import LedgerEntry, Payment


class PaymentFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="paid_at", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="paid_at", lookup_expr="lte")

    class Meta:
        model = Payment
        fields = ("customer", "order", "method", "currency", "is_cancelled")


class LedgerEntryFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = LedgerEntry
        fields = ("customer", "type", "order", "payment")


class CustomerBalanceFilter(django_filters.FilterSet):
    debtors = django_filters.BooleanFilter(method="filter_debtors", label="faqat qarzdorlar")
    over_limit = django_filters.BooleanFilter(
        method="filter_over_limit", label="limitdan oshganlar"
    )

    class Meta:
        model = Customer
        fields = ("manager", "region", "type", "currency", "is_active")

    def filter_debtors(self, queryset, name, value):
        return queryset.filter(balance__gt=0) if value else queryset.filter(balance__lte=0)

    def filter_over_limit(self, queryset, name, value):
        over = queryset.filter(balance__gt=F("credit_limit"))
        return over if value else queryset.exclude(pk__in=over.values("pk"))
