from decimal import Decimal

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.catalog.models import Color, ProductModel, SizeRun, Variant
from apps.customers.models import Customer
from apps.inventory import services as inventory
from apps.inventory.models import Warehouse
from apps.inventory.services import StockLine
from apps.users.models import Role, User
from common.exceptions import BusinessError

from .models import Order, OrderItem

# Savdo menejeri bera oladigan eng katta chegirma; undan kattasini faqat rahbariyat beradi
MAX_MANAGER_DISCOUNT = Decimal("10")

DEFAULT_PRICE_TYPE = {
    Customer.Type.DEALER: Order.PriceType.DEALER,
    Customer.Type.WHOLESALE: Order.PriceType.WHOLESALE,
    Customer.Type.MARKETPLACE: Order.PriceType.WHOLESALE,
    Customer.Type.RETAIL: Order.PriceType.RETAIL,
}

PRICE_FIELD = {
    Order.PriceType.WHOLESALE: "wholesale_price",
    Order.PriceType.DEALER: "dealer_price",
    Order.PriceType.RETAIL: "retail_price",
}

TRANSITIONS = {
    Order.Status.DRAFT: {Order.Status.CONFIRMED, Order.Status.CANCELLED},
    Order.Status.CONFIRMED: {Order.Status.SHIPPED, Order.Status.CANCELLED},
    Order.Status.SHIPPED: {Order.Status.DELIVERED},
    Order.Status.DELIVERED: set(),
    Order.Status.CANCELLED: set(),
}


def _check_discount(user: User, discount: Decimal) -> None:
    if discount > MAX_MANAGER_DISCOUNT and not user.is_management:
        raise BusinessError(
            f"Siz {MAX_MANAGER_DISCOUNT}% dan katta chegirma bera olmaysiz.",
            code="discount_limit",
        )


def _lock(order: Order) -> Order:
    return Order.objects.select_for_update().get(pk=order.pk)


def _ensure_draft(order: Order) -> None:
    if order.status != Order.Status.DRAFT:
        raise BusinessError("Faqat qoralama holatidagi buyurtmani o'zgartirish mumkin.")


def _transition(order: Order, new_status: str) -> None:
    if new_status not in TRANSITIONS[order.status]:
        raise BusinessError(
            f"'{order.get_status_display()}' holatidagi buyurtmani "
            f"'{Order.Status(new_status).label}' holatiga o'tkazib bo'lmaydi."
        )
    order.status = new_status


def _stock_lines(order: Order) -> list[StockLine]:
    return [StockLine(item.variant_id, item.quantity) for item in order.items.all()]


def recalculate_total(order: Order) -> None:
    subtotal = order.items.aggregate(total=Sum(F("quantity") * F("price")))["total"] or 0
    multiplier = (Decimal(100) - order.discount_percent) / Decimal(100)
    order.total_amount = (Decimal(subtotal) * multiplier).quantize(Decimal("0.01"))
    order.save(update_fields=["total_amount", "updated_at"])


def unit_price(order: Order, variant: Variant) -> Decimal:
    product_model = variant.product_model
    if product_model.currency != order.currency:
        raise BusinessError(
            f"{product_model.article} narxi {product_model.currency}da, buyurtma esa "
            f"{order.currency}da. Narxni qo'lda kiriting.",
            code="currency_mismatch",
        )
    return getattr(product_model, PRICE_FIELD[order.price_type])


@transaction.atomic
def create_order(
    *,
    customer: Customer,
    warehouse: Warehouse,
    user: User,
    price_type: str | None = None,
    discount_percent: Decimal = Decimal(0),
    comment: str = "",
) -> Order:
    _check_discount(user, discount_percent)
    manager = customer.manager
    if manager is None and user.role == Role.SALES_MANAGER:
        manager = user
    return Order.objects.create(
        customer=customer,
        manager=manager,
        warehouse=warehouse,
        price_type=price_type or DEFAULT_PRICE_TYPE[customer.type],
        currency=customer.currency,
        discount_percent=discount_percent,
        comment=comment,
        created_by=user,
    )


@transaction.atomic
def update_order(order: Order, *, user: User, **fields) -> Order:
    order = _lock(order)
    _ensure_draft(order)
    if "discount_percent" in fields:
        _check_discount(user, fields["discount_percent"])
    for name, value in fields.items():
        setattr(order, name, value)
    order.save()
    recalculate_total(order)
    return order


def _add(order: Order, variant: Variant, quantity: int, price: Decimal | None) -> OrderItem:
    if not variant.is_active or not variant.product_model.is_active:
        raise BusinessError(f"{variant} sotuvda emas.")
    item = order.items.filter(variant=variant).first()
    if item:
        item.quantity += quantity
        if price is not None:
            item.price = price
        item.save(update_fields=["quantity", "price"])
        return item
    return OrderItem.objects.create(
        order=order,
        variant=variant,
        quantity=quantity,
        price=price if price is not None else unit_price(order, variant),
    )


@transaction.atomic
def add_item(
    order: Order, variant: Variant, quantity: int, price: Decimal | None = None
) -> OrderItem:
    """Qator qo'shadi; bu variant buyurtmada bo'lsa, sonini oshiradi."""
    order = _lock(order)
    _ensure_draft(order)
    item = _add(order, variant, quantity, price)
    recalculate_total(order)
    return item


@transaction.atomic
def add_boxes(
    order: Order, product_model: ProductModel, color: Color, size_run: SizeRun, count: int
) -> list[OrderItem]:
    """
    Korobka bo'yicha qo'shish: razmer qatoridagi har bir razmerdan (juft soni × korobka soni).
    Masalan, {"40": 1, "41": 2} qatoridan 3 korobka = 40-razmerdan 3, 41-razmerdan 6 juft.
    """
    order = _lock(order)
    _ensure_draft(order)
    variants = {
        v.size: v
        for v in product_model.variants.select_related("product_model").filter(
            color=color, size__in=size_run.size_list
        )
    }
    missing = [size for size in size_run.size_list if size not in variants]
    if missing:
        raise BusinessError(
            f"{product_model.article} ({color}) uchun quyidagi razmerlar katalogda yo'q: "
            f"{', '.join(map(str, missing))}.",
            missing_sizes=missing,
        )
    items = [
        _add(order, variants[int(size)], per_box * count, None)
        for size, per_box in size_run.sizes.items()
    ]
    recalculate_total(order)
    return items


@transaction.atomic
def update_item(item: OrderItem, *, quantity: int | None = None, price: Decimal | None = None):
    order = _lock(item.order)
    _ensure_draft(order)
    if quantity is not None:
        item.quantity = quantity
    if price is not None:
        item.price = price
    item.save(update_fields=["quantity", "price"])
    recalculate_total(order)
    return item


@transaction.atomic
def remove_item(item: OrderItem) -> None:
    order = _lock(item.order)
    _ensure_draft(order)
    item.delete()
    recalculate_total(order)


@transaction.atomic
def confirm_order(order: Order, *, user: User) -> Order:
    order = _lock(order)
    _transition(order, Order.Status.CONFIRMED)
    lines = _stock_lines(order)
    if not lines:
        raise BusinessError("Bo'sh buyurtmani tasdiqlab bo'lmaydi.")
    inventory.reserve(order.warehouse, lines)
    order.confirmed_at = timezone.now()
    order.save(update_fields=["status", "confirmed_at", "updated_at"])
    return order


@transaction.atomic
def ship_order(order: Order, *, user: User) -> Order:
    order = _lock(order)
    _transition(order, Order.Status.SHIPPED)
    inventory.ship(order.warehouse, _stock_lines(order), user=user, reference=order.number)
    order.shipped_at = timezone.now()
    order.save(update_fields=["status", "shipped_at", "updated_at"])
    return order


@transaction.atomic
def deliver_order(order: Order, *, user: User) -> Order:
    order = _lock(order)
    _transition(order, Order.Status.DELIVERED)
    order.delivered_at = timezone.now()
    order.save(update_fields=["status", "delivered_at", "updated_at"])
    return order


@transaction.atomic
def cancel_order(order: Order, *, user: User) -> Order:
    order = _lock(order)
    was_confirmed = order.status == Order.Status.CONFIRMED
    _transition(order, Order.Status.CANCELLED)
    if was_confirmed:
        inventory.release(order.warehouse, _stock_lines(order))
    order.cancelled_at = timezone.now()
    order.save(update_fields=["status", "cancelled_at", "updated_at"])
    return order
