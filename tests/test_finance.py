from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from django.utils import timezone
from openpyxl import load_workbook

from apps.finance import services as finance
from apps.finance.models import CurrencyRate, LedgerEntry
from apps.inventory import services as inventory
from apps.inventory.services import StockLine
from apps.orders import services as orders
from apps.users.models import Role

from .factories import CustomerFactory, UserFactory, VariantFactory, WarehouseFactory

pytestmark = pytest.mark.django_db

TODAY = timezone.localdate()


@pytest.fixture
def director():
    return UserFactory(role=Role.DIRECTOR)


@pytest.fixture
def customer():
    return CustomerFactory(currency="USD", credit_limit=Decimal("0"))


@pytest.fixture
def accountant_client(client_for):
    return client_for(Role.ACCOUNTANT)


@pytest.fixture
def make_order(director):
    """Ombordagi mahsulotdan `pairs` juftlik buyurtma (25 USD/juft) yaratadi."""
    warehouse = WarehouseFactory(name="Asosiy ombor")
    variant = VariantFactory(size=41)
    inventory.receive(warehouse, [StockLine(variant.id, 500)], user=None)

    def make(customer, pairs=10, user=director):
        order = orders.create_order(
            customer=customer, warehouse=warehouse, user=user, price_type="wholesale"
        )
        orders.add_item(order, variant, pairs)
        order.refresh_from_db()
        return order

    return make


def balance(customer) -> Decimal:
    return finance.customer_balance(customer)


def test_payment_in_customer_currency(accountant_client, customer):
    response = accountant_client.post(
        "/api/v1/finance/payments/",
        {"customer": customer.id, "amount": "500", "currency": "USD", "method": "bank"},
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["settlement_amount"] == "500.00"
    assert response.data["rate"] is None
    assert response.data["created_by"] == accountant_client.user.id
    assert balance(customer) == Decimal("-500.00")  # oldindan to'lov


def test_uzs_payment_uses_rate_on_payment_date(accountant_client, customer):
    CurrencyRate.objects.create(
        currency="USD", rate=Decimal("12600"), date=TODAY - timedelta(days=5)
    )
    CurrencyRate.objects.create(currency="USD", rate=Decimal("12800"), date=TODAY)

    response = accountant_client.post(
        "/api/v1/finance/payments/",
        {
            "customer": customer.id,
            "amount": "1260000",
            "currency": "UZS",
            "method": "cash",
            "paid_at": str(TODAY - timedelta(days=2)),
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["rate"] == "12600.0000"
    assert response.data["settlement_amount"] == "100.00"


def test_explicit_rate_overrides_stored_rate(accountant_client, customer):
    CurrencyRate.objects.create(currency="USD", rate=Decimal("12600"), date=TODAY)
    response = accountant_client.post(
        "/api/v1/finance/payments/",
        {
            "customer": customer.id,
            "amount": "1300000",
            "currency": "UZS",
            "method": "cash",
            "rate": "13000",
        },
        format="json",
    )
    assert response.data["settlement_amount"] == "100.00"


def test_payment_without_rate_is_rejected(accountant_client, customer):
    response = accountant_client.post(
        "/api/v1/finance/payments/",
        {"customer": customer.id, "amount": "100000", "currency": "UZS", "method": "cash"},
        format="json",
    )
    assert response.status_code == 400
    assert response.data["code"] == "rate_missing"


def test_cancel_payment_adds_reversal(accountant_client, customer):
    payment = finance.register_payment(
        customer=customer, amount=Decimal("200"), currency="USD", method="cash", user=None
    )
    url = f"/api/v1/finance/payments/{payment.id}/cancel/"

    response = accountant_client.post(url, {"reason": "Xato kiritildi"}, format="json")
    assert response.status_code == 200
    assert response.data["is_cancelled"] is True
    assert balance(customer) == 0
    assert list(customer.ledger_entries.values_list("type", flat=True)) == [
        LedgerEntry.Type.PAYMENT,
        LedgerEntry.Type.PAYMENT_CANCEL,
    ]
    assert accountant_client.post(url, {"reason": "yana"}, format="json").status_code == 400


def test_payment_order_must_belong_to_customer(accountant_client, customer, make_order):
    foreign_order = make_order(CustomerFactory())
    response = accountant_client.post(
        "/api/v1/finance/payments/",
        {
            "customer": customer.id,
            "order": foreign_order.id,
            "amount": "10",
            "currency": "USD",
            "method": "cash",
        },
        format="json",
    )
    assert response.status_code == 400


def test_payments_cannot_be_edited_or_deleted(accountant_client, customer):
    payment = finance.register_payment(
        customer=customer, amount=Decimal("10"), currency="USD", method="cash", user=None
    )
    url = f"/api/v1/finance/payments/{payment.id}/"
    assert accountant_client.patch(url, {"amount": "1"}, format="json").status_code == 405
    assert accountant_client.delete(url).status_code == 405


class TestReconciliation:
    @pytest.fixture
    def history(self, customer, director):
        """Davrdan oldin 1000 qarz, davr ichida 250 jo'natish va 600 to'lov."""
        finance.add_adjustment(
            customer,
            Decimal("1000"),
            user=director,
            description="Eski qarz",
            entry_date=date(2026, 9, 1),
            opening=True,
        )
        finance.add_adjustment(
            customer,
            Decimal("250"),
            user=director,
            description="Jo'natish",
            entry_date=date(2026, 10, 5),
        )
        finance.register_payment(
            customer=customer,
            amount=Decimal("600"),
            currency="USD",
            method="bank",
            paid_at=date(2026, 10, 20),
            user=None,
        )
        return customer

    def url(self, customer):
        return f"/api/v1/finance/balances/{customer.id}/reconciliation/"

    def test_json(self, accountant_client, history):
        response = accountant_client.get(
            self.url(history), {"date_from": "2026-10-01", "date_to": "2026-10-31"}
        )
        assert response.status_code == 200
        data = response.data
        assert data["opening_balance"] == "1000.00"
        assert data["debit_total"] == "250.00"
        assert data["credit_total"] == "600.00"
        assert data["closing_balance"] == "650.00"
        assert [row["balance"] for row in data["rows"]] == ["1250.00", "650.00"]
        assert data["rows"][1]["reference"].startswith("T-")

    def test_xlsx_export(self, accountant_client, history):
        response = accountant_client.get(
            self.url(history),
            {"date_from": "2026-10-01", "date_to": "2026-10-31", "export": "xlsx"},
        )
        assert response.status_code == 200
        assert response["Content-Type"].startswith("application/vnd.openxmlformats")
        assert "attachment" in response["Content-Disposition"]

        sheet = load_workbook(BytesIO(response.content)).active
        values = [[c for c in row if c is not None] for row in sheet.iter_rows(values_only=True)]
        assert ["Boshlang'ich qoldiq", 1000] in values
        assert ["Yakuniy qoldiq", 650] in values

    def test_invalid_period(self, accountant_client, history):
        response = accountant_client.get(
            self.url(history), {"date_from": "2026-10-31", "date_to": "2026-10-01"}
        )
        assert response.status_code == 400


def test_balances_list_and_scope(client_for):
    manager_client = client_for(Role.SALES_MANAGER)
    debtor = CustomerFactory(manager=manager_client.user, credit_limit=Decimal("100"))
    prepaid = CustomerFactory(manager=manager_client.user)
    foreign = CustomerFactory()
    for c, amount in ((debtor, "300"), (prepaid, "-50"), (foreign, "999")):
        finance.add_adjustment(c, Decimal(amount), user=None, description="test")

    rows = manager_client.get("/api/v1/finance/balances/").data["results"]
    assert [(r["id"], r["balance"]) for r in rows] == [
        (debtor.id, "300.00"),
        (prepaid.id, "-50.00"),
    ]
    assert rows[0]["available_credit"] == "-200.00"

    debtors = manager_client.get("/api/v1/finance/balances/", {"debtors": True}).data["results"]
    assert [r["id"] for r in debtors] == [debtor.id]
    over = manager_client.get("/api/v1/finance/balances/", {"over_limit": True}).data["results"]
    assert [r["id"] for r in over] == [debtor.id]


def test_balance_is_not_multiplied_by_joins(accountant_client, customer):
    """Bir nechta to'lov va yozuv bo'lganda ham balans to'g'ri yig'iladi (JOIN dublikati yo'q)."""
    for _ in range(3):
        finance.register_payment(
            customer=customer, amount=Decimal("10"), currency="USD", method="cash", user=None
        )
    finance.add_adjustment(customer, Decimal("100"), user=None, description="test")

    row = accountant_client.get(f"/api/v1/finance/balances/{customer.id}/").data
    assert row["balance"] == "70.00"
    assert row["last_payment_date"] == str(TODAY)


def test_sales_manager_can_read_but_not_pay(client_for):
    manager_client = client_for(Role.SALES_MANAGER)
    customer = CustomerFactory(manager=manager_client.user)
    assert manager_client.get("/api/v1/finance/payments/").status_code == 200
    response = manager_client.post(
        "/api/v1/finance/payments/",
        {"customer": customer.id, "amount": "10", "currency": "USD", "method": "cash"},
        format="json",
    )
    assert response.status_code == 403


def test_adjustment_endpoint(accountant_client, client_for, customer):
    payload = {"customer": customer.id, "amount": "-15.50", "description": "Chegirma"}
    response = accountant_client.post("/api/v1/finance/ledger/adjustment/", payload, format="json")
    assert response.status_code == 201
    assert response.data["type"] == "adjustment"
    assert balance(customer) == Decimal("-15.50")

    assert (
        client_for(Role.SALES_MANAGER)
        .post("/api/v1/finance/ledger/adjustment/", payload, format="json")
        .status_code
        == 403
    )


def test_customer_currency_is_locked_after_ledger(client_for, customer):
    client = client_for(Role.DIRECTOR)
    url = f"/api/v1/customers/{customer.id}/"
    assert client.patch(url, {"currency": "UZS"}, format="json").status_code == 200
    assert client.patch(url, {"currency": "USD"}, format="json").status_code == 200

    finance.add_adjustment(customer, Decimal("1"), user=None, description="test")
    response = client.patch(url, {"currency": "UZS"}, format="json")
    assert response.status_code == 400
    assert "currency" in response.data


class TestCbuRates:
    @pytest.fixture
    def cbu(self, monkeypatch):
        calls = []

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return [{"Ccy": "USD", "Rate": "12650.55", "Nominal": "1", "Date": "02.11.2026"}]

        def fake_get(url, timeout):
            calls.append(url)
            return FakeResponse()

        monkeypatch.setattr(finance.requests, "get", fake_get)
        return calls

    def test_fetch_saves_rate(self, cbu):
        saved = finance.fetch_cbu_rates(date(2026, 11, 2))
        assert cbu == ["https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/2026-11-02/"]
        assert [(r.currency, r.rate, r.date, r.source) for r in saved] == [
            ("USD", Decimal("12650.55"), date(2026, 11, 2), "cbu")
        ]
        # Qayta chaqirilsa dublikat yaratilmaydi
        finance.fetch_cbu_rates(date(2026, 11, 2))
        assert CurrencyRate.objects.count() == 1

    def test_manual_rate_is_not_overwritten(self, cbu):
        CurrencyRate.objects.create(currency="USD", rate=Decimal("12700"), date=date(2026, 11, 2))
        assert finance.fetch_cbu_rates(date(2026, 11, 2)) == []
        assert CurrencyRate.objects.get().rate == Decimal("12700")

    def test_celery_task(self, cbu):
        from apps.finance.tasks import fetch_cbu_rates

        assert fetch_cbu_rates.delay().get() == ["2026-11-02: 1 USD = 12650.55 so'm"]
