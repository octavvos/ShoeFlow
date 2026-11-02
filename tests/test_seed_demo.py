import pytest
from django.core.management import call_command

from apps.catalog.models import ProductModel, Variant
from apps.customers.models import Customer
from apps.finance.models import LedgerEntry, Payment
from apps.inventory.models import StockBalance, StockMovement, Warehouse
from apps.orders.models import Order
from apps.users.models import User

pytestmark = pytest.mark.django_db


def test_seed_demo_creates_data_and_is_idempotent():
    call_command("seed_demo")

    assert User.objects.filter(username="direktor").exists()
    assert ProductModel.objects.count() == 8
    assert Variant.objects.count() > 0
    assert Customer.objects.count() == 12
    assert all(c.manager_id for c in Customer.objects.all())
    assert Warehouse.objects.count() == 2
    assert StockMovement.objects.filter(type=StockMovement.Type.SHIPMENT).exists()
    assert set(Order.objects.values_list("status", flat=True)) == set(Order.Status.values)

    # Rezerv faqat tasdiqlangan (hali jo'natilmagan) buyurtmalardan iborat bo'lishi kerak
    confirmed_pairs = sum(
        item.quantity
        for order in Order.objects.filter(status=Order.Status.CONFIRMED)
        for item in order.items.all()
    )
    assert sum(StockBalance.objects.values_list("reserved", flat=True)) == confirmed_pairs

    # Har bir jo'natilgan buyurtma mijoz hisobiga yozilgan
    shipped = Order.objects.filter(status__in=[Order.Status.SHIPPED, Order.Status.DELIVERED])
    assert LedgerEntry.objects.filter(type=LedgerEntry.Type.SHIPMENT).count() == shipped.count()
    assert Payment.objects.filter(currency="UZS").exists()
    assert Payment.objects.filter(is_cancelled=True).count() == 1

    counts = (User.objects.count(), Variant.objects.count(), Customer.objects.count())
    call_command("seed_demo")
    assert (User.objects.count(), Variant.objects.count(), Customer.objects.count()) == counts


def test_demo_user_can_log_in(api_client):
    call_command("seed_demo")
    response = api_client.post(
        "/api/v1/auth/token/", {"username": "menejer1", "password": "Demo-12345"}, format="json"
    )
    assert response.status_code == 200
