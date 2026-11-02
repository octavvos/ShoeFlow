"""
Ikki menejer bir vaqtda omborda qolgan oxirgi mahsulotni o'z buyurtmasiga tasdiqlamoqchi.
select_for_update tufayli faqat bittasi muvaffaqiyatli bo'lishi kerak — qoldiq minusga ketmaydi.
"""

import threading

import pytest
from django.db import connection

from apps.inventory import services as inventory
from apps.inventory.models import StockBalance
from apps.inventory.services import InsufficientStock, StockLine
from apps.orders import services
from apps.orders.models import Order
from apps.users.models import Role

from .factories import CustomerFactory, UserFactory, VariantFactory, WarehouseFactory


@pytest.mark.django_db(transaction=True)
def test_two_managers_cannot_reserve_the_same_last_pairs():
    warehouse = WarehouseFactory(name="Asosiy ombor")
    variant = VariantFactory(size=42)
    inventory.receive(warehouse, [StockLine(variant.id, 8)], user=None)

    orders = []
    for _ in range(2):
        manager = UserFactory(role=Role.SALES_MANAGER)
        order = services.create_order(
            customer=CustomerFactory(manager=manager), warehouse=warehouse, user=manager
        )
        services.add_item(order, variant, 8)
        orders.append(order)

    barrier = threading.Barrier(len(orders))
    results = []

    def confirm(order):
        try:
            barrier.wait()
            services.confirm_order(order, user=order.manager)
            results.append("ok")
        except InsufficientStock:
            results.append("shortage")
        finally:
            connection.close()

    threads = [threading.Thread(target=confirm, args=(o,)) for o in orders]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert sorted(results) == ["ok", "shortage"]
    assert Order.objects.filter(status=Order.Status.CONFIRMED).count() == 1
    balance = StockBalance.objects.get(warehouse=warehouse, variant=variant)
    assert (balance.quantity, balance.reserved) == (8, 8)
