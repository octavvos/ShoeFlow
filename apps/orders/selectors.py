from django.db.models import Count, QuerySet, Sum
from django.db.models.functions import Coalesce

from apps.users.models import Role, User

from .models import Order


def _scope(qs: QuerySet[Order], user: User) -> QuerySet[Order]:
    """Savdo menejeri faqat o'z mijozlarining buyurtmalarini ko'radi."""
    if not user.is_authenticated:
        return qs.none()
    if not user.is_superuser and user.role == Role.SALES_MANAGER:
        qs = qs.filter(customer__manager=user)
    return qs


def visible_orders(user: User) -> QuerySet[Order]:
    # GROUP BY'li so'rovda Meta.ordering ishlamaydi, shuning uchun tartib aniq beriladi
    qs = (
        Order.objects.select_related("customer", "manager", "warehouse")
        .annotate(total_pairs=Coalesce(Sum("items__quantity"), 0))
        .order_by("-created_at", "-id")
    )
    return _scope(qs, user)


def order_status_counts(user: User) -> dict[str, int]:
    """Har bir holatdagi buyurtmalar soni — bitta GROUP BY so'rovi bilan."""
    rows = _scope(Order.objects.all(), user).values("status").annotate(n=Count("id")).order_by()
    counts = dict.fromkeys(Order.Status.values, 0)
    counts.update({row["status"]: row["n"] for row in rows})
    return counts
