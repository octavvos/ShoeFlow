import django_filters

from .models import Customer


class CustomerFilter(django_filters.FilterSet):
    tag = django_filters.CharFilter(method="filter_tag", label="teg")

    class Meta:
        model = Customer
        fields = ("type", "region", "manager", "currency", "is_active")

    def filter_tag(self, queryset, name, value):
        return queryset.filter(tags__contains=[value])
