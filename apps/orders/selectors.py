from django.db.models import QuerySet, Sum
from django.db.models.functions import Coalesce

from apps.users.models import Role, User

from .models import Order


def visible_orders(user: User) -> QuerySet[Order]:
    """Savdo menejeri faqat o'z mijozlarining buyurtmalarini ko'radi."""
    # GROUP BY'li so'rovda Meta.ordering ishlamaydi, shuning uchun tartib aniq beriladi
    qs = (
        Order.objects.select_related("customer", "manager", "warehouse")
        .annotate(total_pairs=Coalesce(Sum("items__quantity"), 0))
        .order_by("-created_at", "-id")
    )
    if not user.is_authenticated:
        return qs.none()
    if not user.is_superuser and user.role == Role.SALES_MANAGER:
        qs = qs.filter(customer__manager=user)
    return qs
