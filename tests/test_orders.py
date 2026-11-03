from decimal import Decimal

import pytest

from apps.catalog.services import generate_variants
from apps.inventory import services as inventory
from apps.inventory.models import StockBalance, StockMovement
from apps.inventory.services import StockLine
from apps.orders.models import Order
from apps.users.models import Role

from .factories import (
    ColorFactory,
    CustomerFactory,
    ProductModelFactory,
    SizeRunFactory,
    UserFactory,
    WarehouseFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def warehouse():
    return WarehouseFactory(name="Asosiy ombor")


@pytest.fixture
def black():
    return ColorFactory(name="Qora")


@pytest.fixture
def product(black):
    """Erkaklar tuflisi: 40–43 razmerlar, korobkada 40/43 dan 1, 41/42 dan 2 juft."""
    size_run = SizeRunFactory(sizes={"40": 1, "41": 2, "42": 2, "43": 1})
    model = ProductModelFactory(
        default_size_run=size_run,
        wholesale_price=Decimal("25.00"),
        dealer_price=Decimal("22.00"),
        retail_price=Decimal("35.00"),
    )
    generate_variants(model, [black], size_run.size_list)
    return model


@pytest.fixture
def variants(product):
    return {v.size: v for v in product.variants.all()}


@pytest.fixture
def stocked(warehouse, variants):
    inventory.receive(warehouse, [StockLine(v.id, 20) for v in variants.values()], user=None)


@pytest.fixture
def manager_client(client_for):
    return client_for(Role.SALES_MANAGER)


@pytest.fixture
def order_url(manager_client, warehouse):
    """Menejerning diler-mijozi uchun yangi qoralama buyurtma."""
    customer = CustomerFactory(manager=manager_client.user, type="dealer")
    response = manager_client.post(
        "/api/v1/orders/", {"customer": customer.id, "warehouse": warehouse.id}, format="json"
    )
    assert response.status_code == 201, response.data
    return f"/api/v1/orders/{response.data['id']}/"


def reserved(warehouse, variant):
    return StockBalance.objects.get(warehouse=warehouse, variant=variant).reserved


def test_new_order_takes_defaults_from_customer(manager_client, order_url):
    order = manager_client.get(order_url).data
    assert order["status"] == "draft"
    assert order["price_type"] == "dealer"
    assert order["currency"] == "USD"
    assert order["manager"] == manager_client.user.id
    assert order["number"].startswith("Z-")


def test_add_item_uses_catalog_price_and_merges(manager_client, order_url, variants):
    manager_client.post(order_url + "items/", {"variant": variants[41].id, "quantity": 3})
    order = manager_client.post(
        order_url + "items/", {"variant": variants[41].id, "quantity": 2}, format="json"
    ).data

    assert len(order["items"]) == 1
    assert order["items"][0]["quantity"] == 5
    assert order["items"][0]["price"] == "22.00"  # diler narxi
    assert order["total_amount"] == "110.00"


def test_add_boxes_expands_size_run(manager_client, order_url, product, black):
    order = manager_client.post(
        order_url + "boxes/",
        {"product_model": product.id, "color": black.id, "count": 3},
        format="json",
    ).data

    assert {i["size"]: i["quantity"] for i in order["items"]} == {40: 3, 41: 6, 42: 6, 43: 3}
    assert order["total_pairs"] == 18
    assert order["total_amount"] == str(Decimal("22.00") * 18)


def test_add_boxes_reports_missing_sizes(manager_client, order_url, product, black):
    wide_run = SizeRunFactory(sizes={"40": 1, "44": 1, "45": 1})
    response = manager_client.post(
        order_url + "boxes/",
        {"product_model": product.id, "color": black.id, "size_run": wide_run.id, "count": 1},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["missing_sizes"] == [44, 45]


def test_currency_mismatch_requires_manual_price(manager_client, warehouse, variants):
    customer = CustomerFactory(manager=manager_client.user, currency="UZS")
    url = "/api/v1/orders/{}/items/".format(
        manager_client.post(
            "/api/v1/orders/", {"customer": customer.id, "warehouse": warehouse.id}, format="json"
        ).data["id"]
    )

    response = manager_client.post(url, {"variant": variants[40].id, "quantity": 1}, format="json")
    assert response.status_code == 400
    assert response.data["code"] == "currency_mismatch"

    response = manager_client.post(
        url, {"variant": variants[40].id, "quantity": 1, "price": "320000"}, format="json"
    )
    assert response.status_code == 201


def test_discount_limit_for_sales_manager(client_for, manager_client, order_url, variants):
    manager_client.post(order_url + "items/", {"variant": variants[40].id, "quantity": 10})

    response = manager_client.patch(order_url, {"discount_percent": "15"}, format="json")
    assert response.status_code == 400
    assert response.data["code"] == "discount_limit"

    response = client_for(Role.DIRECTOR).patch(order_url, {"discount_percent": "15"}, format="json")
    assert response.status_code == 200
    assert response.data["total_amount"] == "187.00"  # 220 - 15%


def test_full_order_lifecycle(client_for, manager_client, order_url, warehouse, variants, stocked):
    manager_client.post(order_url + "items/", {"variant": variants[42].id, "quantity": 5})

    assert manager_client.post(order_url + "confirm/").data["status"] == "confirmed"
    assert reserved(warehouse, variants[42]) == 5

    warehouse_client = client_for(Role.WAREHOUSE)
    order = warehouse_client.post(order_url + "ship/").data
    assert order["status"] == "shipped"
    balance = StockBalance.objects.get(warehouse=warehouse, variant=variants[42])
    assert (balance.quantity, balance.reserved) == (15, 0)

    shipment = StockMovement.objects.get(type=StockMovement.Type.SHIPMENT)
    assert shipment.quantity == -5
    assert shipment.reference == order["number"]
    assert shipment.created_by == warehouse_client.user

    order = warehouse_client.post(order_url + "deliver/").data
    assert order["status"] == "delivered"
    assert order["delivered_at"] is not None


def test_confirm_with_insufficient_stock(manager_client, order_url, warehouse, variants, stocked):
    manager_client.post(order_url + "items/", {"variant": variants[40].id, "quantity": 5})
    manager_client.post(order_url + "items/", {"variant": variants[43].id, "quantity": 25})

    response = manager_client.post(order_url + "confirm/")

    assert response.status_code == 400
    assert response.data["shortages"][0]["size"] == 43
    assert response.data["shortages"][0]["available"] == 20
    assert manager_client.get(order_url).data["status"] == "draft"
    assert reserved(warehouse, variants[40]) == 0


def test_cancel_confirmed_order_releases_reservation(
    manager_client, order_url, warehouse, variants, stocked
):
    manager_client.post(order_url + "items/", {"variant": variants[41].id, "quantity": 4})
    manager_client.post(order_url + "confirm/")
    assert reserved(warehouse, variants[41]) == 4

    assert manager_client.post(order_url + "cancel/").data["status"] == "cancelled"
    assert reserved(warehouse, variants[41]) == 0


def test_confirmed_order_items_are_locked(manager_client, order_url, variants, stocked):
    order = manager_client.post(
        order_url + "items/", {"variant": variants[41].id, "quantity": 1}, format="json"
    ).data
    item_id = order["items"][0]["id"]
    manager_client.post(order_url + "confirm/")

    assert (
        manager_client.post(
            order_url + "items/", {"variant": variants[40].id, "quantity": 1}
        ).status_code
        == 400
    )
    assert manager_client.patch(f"{order_url}items/{item_id}/", {"quantity": 9}).status_code == 400
    assert manager_client.delete(f"{order_url}items/{item_id}/").status_code == 400


def test_update_and_remove_item(manager_client, order_url, variants):
    order = manager_client.post(
        order_url + "items/", {"variant": variants[41].id, "quantity": 1}, format="json"
    ).data
    item_url = f"{order_url}items/{order['items'][0]['id']}/"

    order = manager_client.patch(item_url, {"quantity": 4, "price": "20"}, format="json").data
    assert order["total_amount"] == "80.00"

    order = manager_client.delete(item_url).data
    assert order["items"] == []
    assert order["total_amount"] == "0.00"


@pytest.mark.parametrize("action", ["ship", "deliver"])
def test_invalid_transition_from_draft(client_for, order_url, action):
    response = client_for(Role.WAREHOUSE).post(order_url + f"{action}/")
    assert response.status_code == 400
    assert "Qoralama" in response.data["detail"]


def test_empty_order_cannot_be_confirmed(manager_client, order_url):
    assert manager_client.post(order_url + "confirm/").status_code == 400


def test_role_permissions_on_actions(client_for, manager_client, order_url, variants, stocked):
    manager_client.post(order_url + "items/", {"variant": variants[40].id, "quantity": 1})

    assert client_for(Role.WAREHOUSE).post(order_url + "confirm/").status_code == 403
    manager_client.post(order_url + "confirm/")
    assert manager_client.post(order_url + "ship/").status_code == 403
    assert client_for(Role.ACCOUNTANT).get(order_url).status_code == 200
    assert client_for(Role.WORKER).get(order_url).status_code == 403


def test_sales_manager_isolation(client_for, warehouse, order_url):
    other = client_for(UserFactory(role=Role.SALES_MANAGER))
    assert other.get(order_url).status_code == 404
    assert other.get("/api/v1/orders/").data["count"] == 0

    foreign_customer = Order.objects.get().customer
    response = other.post(
        "/api/v1/orders/",
        {"customer": foreign_customer.id, "warehouse": warehouse.id},
        format="json",
    )
    assert response.status_code == 400
    assert "customer" in response.data


def test_orders_are_not_deleted(manager_client, order_url):
    assert manager_client.delete(order_url).status_code == 405


def test_filter_by_status(client_for, manager_client, order_url, variants, stocked):
    manager_client.post(order_url + "items/", {"variant": variants[40].id, "quantity": 1})
    manager_client.post(order_url + "confirm/")

    director = client_for(Role.DIRECTOR)
    assert director.get("/api/v1/orders/", {"status": "confirmed"}).data["count"] == 1
    assert director.get("/api/v1/orders/", {"status": "draft"}).data["count"] == 0


def test_status_stats_are_scoped_to_manager(
    client_for, manager_client, order_url, variants, stocked
):
    manager_client.post(order_url + "items/", {"variant": variants[40].id, "quantity": 1})
    manager_client.post(order_url + "confirm/")
    other = client_for(UserFactory(role=Role.SALES_MANAGER))
    other_customer = CustomerFactory(manager=other.user)
    other.post(
        "/api/v1/orders/",
        {"customer": other_customer.id, "warehouse": Order.objects.get().warehouse_id},
        format="json",
    )

    own = manager_client.get("/api/v1/orders/stats/").data
    assert own == {"draft": 0, "confirmed": 1, "shipped": 0, "delivered": 0, "cancelled": 0}

    everything = client_for(Role.DIRECTOR).get("/api/v1/orders/stats/").data
    assert everything["draft"] == 1 and everything["confirmed"] == 1


def test_status_stats_single_query(client_for, django_assert_max_num_queries):
    client = client_for(Role.DIRECTOR)
    with django_assert_max_num_queries(3):  # sessiya/auth + bitta GROUP BY
        assert client.get("/api/v1/orders/stats/").status_code == 200
