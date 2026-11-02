from django.db.models import QuerySet

from apps.users.models import Role, User

from .models import Customer


def visible_customers(user: User) -> QuerySet[Customer]:
    """Savdo menejeri faqat o'ziga biriktirilgan mijozlarni ko'radi."""
    qs = Customer.objects.select_related("manager")
    if not user.is_authenticated:
        return qs.none()
    if not user.is_superuser and user.role == Role.SALES_MANAGER:
        qs = qs.filter(manager=user)
    return qs
