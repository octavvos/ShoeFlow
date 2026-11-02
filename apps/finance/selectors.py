from decimal import Decimal

from django.db.models import (
    DecimalField,
    ExpressionWrapper,
    F,
    OuterRef,
    QuerySet,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce

from apps.customers.models import Customer
from apps.customers.selectors import visible_customers
from apps.orders.models import Order
from apps.users.models import User

from .models import LedgerEntry, Payment

MONEY = DecimalField(max_digits=14, decimal_places=2)


def _subquery_sum(queryset, field_name: str):
    # Bir nechta JOIN bilan Sum qilinsa qatorlar ko'payib, summa noto'g'ri chiqadi —
    # shuning uchun har bir yig'indi alohida subquery
    total = queryset.values("customer").annotate(total=Sum(field_name)).values("total")
    return Coalesce(Subquery(total, output_field=MONEY), Value(Decimal(0)), output_field=MONEY)


def customer_balances(user: User) -> QuerySet[Customer]:
    qs = visible_customers(user).annotate(
        balance=_subquery_sum(LedgerEntry.objects.filter(customer=OuterRef("pk")), "amount"),
        open_orders_amount=_subquery_sum(
            Order.objects.filter(customer=OuterRef("pk"), status=Order.Status.CONFIRMED),
            "total_amount",
        ),
        last_payment_date=Subquery(
            Payment.objects.filter(customer=OuterRef("pk"), is_cancelled=False)
            .order_by("-paid_at")
            .values("paid_at")[:1]
        ),
    )
    return qs.annotate(
        available_credit=ExpressionWrapper(
            F("credit_limit") - F("balance") - F("open_orders_amount"), output_field=MONEY
        )
    )
