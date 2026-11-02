import pytest

from apps.inventory import services
from apps.inventory.models import StockBalance, StockMovement
from apps.inventory.services import StockLine
from apps.users.models import Role
from common.exceptions import BusinessError

from .factories import VariantFactory, WarehouseFactory

pytestmark = pytest.mark.django_db


def balance(warehouse, variant) -> StockBalance:
    return StockBalance.objects.get(warehouse=warehouse, variant=variant)


@pytest.fixture
def warehouse():
    return WarehouseFactory(name="Asosiy ombor")


@pytest.fixture
def variant():
    return VariantFactory(size=41)


def test_receive_creates_balance_and_movement(client_for, warehouse, variant):
    response = client_for(Role.WAREHOUSE).post(
        "/api/v1/stock-movements/receive/",
        {
            "warehouse": warehouse.id,
            "items": [
                {"variant": variant.id, "quantity": 10},
                {"variant": variant.id, "quantity": 2},
            ],
            "reference": "Partiya #7",
        },
        format="json",
    )
    assert response.status_code == 201
    # Bir xil variantning qatorlari bitta harakatga birlashadi
    assert len(response.data) == 1
    assert response.data[0]["quantity"] == 12
    assert response.data[0]["balance_after"] == 12
    assert balance(warehouse, variant).quantity == 12


def test_write_off_more_than_available_is_rejected(client_for, warehouse, variant):
    services.receive(warehouse, [StockLine(variant.id, 5)], user=None)
    services.reserve(warehouse, [StockLine(variant.id, 3)])

    response = client_for(Role.WAREHOUSE).post(
        "/api/v1/stock-movements/write-off/",
        {
            "warehouse": warehouse.id,
            "items": [{"variant": variant.id, "quantity": 3}],
            "comment": "Brak",
        },
        format="json",
    )
    assert response.status_code == 400
    assert response.data["shortages"][0] == {
        "variant": variant.id,
        "article": variant.product_model.article,
        "color": variant.color.name,
        "size": 41,
        "requested": 3,
        "available": 2,
    }
    assert balance(warehouse, variant).quantity == 5


def test_write_off(warehouse, variant):
    services.receive(warehouse, [StockLine(variant.id, 5)], user=None)
    services.write_off(warehouse, [StockLine(variant.id, 2)], user=None, comment="Brak")
    assert balance(warehouse, variant).quantity == 3


def test_adjust_records_difference(warehouse, variant):
    services.receive(warehouse, [StockLine(variant.id, 10)], user=None)
    movement = services.adjust(warehouse, variant, 7, user=None)

    assert movement.type == StockMovement.Type.ADJUSTMENT
    assert movement.quantity == -3
    assert balance(warehouse, variant).quantity == 7
    assert services.adjust(warehouse, variant, 7, user=None) is None


def test_adjust_below_reserved_is_rejected(warehouse, variant):
    services.receive(warehouse, [StockLine(variant.id, 10)], user=None)
    services.reserve(warehouse, [StockLine(variant.id, 6)])
    with pytest.raises(BusinessError):
        services.adjust(warehouse, variant, 5, user=None)


def test_transfer_between_warehouses(warehouse, variant):
    branch = WarehouseFactory(name="Samarqand filiali")
    services.receive(warehouse, [StockLine(variant.id, 10)], user=None)

    movements = services.transfer(warehouse, branch, [StockLine(variant.id, 4)], user=None)

    assert {m.type for m in movements} == {"transfer_out", "transfer_in"}
    assert balance(warehouse, variant).quantity == 6
    assert balance(branch, variant).quantity == 4


def test_transfer_to_same_warehouse_is_rejected(warehouse, variant):
    with pytest.raises(BusinessError):
        services.transfer(warehouse, warehouse, [StockLine(variant.id, 1)], user=None)


def test_reserve_is_all_or_nothing(warehouse):
    enough, scarce = VariantFactory(size=40), VariantFactory(size=42)
    services.receive(warehouse, [StockLine(enough.id, 10), StockLine(scarce.id, 1)], user=None)

    with pytest.raises(services.InsufficientStock) as exc:
        services.reserve(warehouse, [StockLine(enough.id, 5), StockLine(scarce.id, 2)])

    assert [s["variant"] for s in exc.value.extra["shortages"]] == [scarce.id]
    assert balance(warehouse, enough).reserved == 0


def test_stock_list_shows_available_and_filters_low(client_for, warehouse):
    low, plenty = VariantFactory(size=40), VariantFactory(size=43)
    services.receive(warehouse, [StockLine(low.id, 3), StockLine(plenty.id, 50)], user=None)
    services.reserve(warehouse, [StockLine(plenty.id, 10)])

    client = client_for(Role.SALES_MANAGER)
    rows = client.get("/api/v1/stock/", {"warehouse": warehouse.id}).data["results"]
    assert {r["variant"]: r["available"] for r in rows} == {low.id: 3, plenty.id: 40}

    rows = client.get("/api/v1/stock/", {"available_lte": 5}).data["results"]
    assert [r["variant"] for r in rows] == [low.id]


def test_sales_manager_cannot_change_stock(client_for, warehouse, variant):
    response = client_for(Role.SALES_MANAGER).post(
        "/api/v1/stock-movements/receive/",
        {"warehouse": warehouse.id, "items": [{"variant": variant.id, "quantity": 1}]},
        format="json",
    )
    assert response.status_code == 403


def test_movements_are_immutable(client_for, warehouse, variant):
    movement = services.receive(warehouse, [StockLine(variant.id, 1)], user=None)[0]
    client = client_for(Role.ADMIN)
    assert client.delete(f"/api/v1/stock-movements/{movement.id}/").status_code == 405
    assert client.patch(f"/api/v1/stock-movements/{movement.id}/", {}).status_code == 405


def test_receive_into_inactive_warehouse_is_rejected(client_for, variant):
    closed = WarehouseFactory(name="Yopilgan ombor", is_active=False)
    response = client_for(Role.WAREHOUSE).post(
        "/api/v1/stock-movements/receive/",
        {"warehouse": closed.id, "items": [{"variant": variant.id, "quantity": 1}]},
        format="json",
    )
    assert response.status_code == 400
    assert "warehouse" in response.data
