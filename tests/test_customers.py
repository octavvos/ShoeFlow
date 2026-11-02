import pytest

from apps.customers.models import Customer
from apps.users.models import Role

from .factories import CustomerFactory, UserFactory

pytestmark = pytest.mark.django_db

CUSTOMER_PAYLOAD = {
    "name": "Oyoq kiyim savdo MChJ",
    "type": "dealer",
    "phone": "+998901234567",
    "region": "samarkand",
    "inn": "301234567",
    "tags": ["vip"],
}


def test_sales_manager_sees_only_own_customers(client_for):
    client = client_for(Role.SALES_MANAGER)
    own = CustomerFactory(manager=client.user)
    CustomerFactory()  # boshqa menejerning mijozi

    response = client.get("/api/v1/customers/")
    assert response.status_code == 200
    assert [c["id"] for c in response.data["results"]] == [own.id]


def test_director_sees_all_customers(client_for):
    CustomerFactory.create_batch(3)
    response = client_for(Role.DIRECTOR).get("/api/v1/customers/")
    assert response.data["count"] == 3


def test_sales_manager_cannot_open_foreign_customer(client_for):
    foreign = CustomerFactory()
    response = client_for(Role.SALES_MANAGER).get(f"/api/v1/customers/{foreign.id}/")
    assert response.status_code == 404


def test_customer_created_by_sales_manager_is_assigned_to_them(client_for):
    client = client_for(Role.SALES_MANAGER)
    other_manager = UserFactory(role=Role.SALES_MANAGER)

    response = client.post(
        "/api/v1/customers/", {**CUSTOMER_PAYLOAD, "manager": other_manager.id}, format="json"
    )
    assert response.status_code == 201
    assert response.data["manager"] == client.user.id


def test_only_sales_manager_can_be_assigned(client_for):
    worker = UserFactory(role=Role.WORKER)
    response = client_for(Role.DIRECTOR).post(
        "/api/v1/customers/", {**CUSTOMER_PAYLOAD, "manager": worker.id}, format="json"
    )
    assert response.status_code == 400
    assert "manager" in response.data


@pytest.mark.parametrize(
    ("field", "value"),
    [("phone", "901234567"), ("inn", "12345"), ("credit_limit", "-1")],
)
def test_invalid_customer_fields_rejected(client_for, field, value):
    response = client_for(Role.DIRECTOR).post(
        "/api/v1/customers/", {**CUSTOMER_PAYLOAD, field: value}, format="json"
    )
    assert response.status_code == 400
    assert field in response.data


def test_duplicate_inn_rejected_but_empty_inn_allowed(client_for):
    client = client_for(Role.DIRECTOR)
    assert client.post("/api/v1/customers/", CUSTOMER_PAYLOAD, format="json").status_code == 201
    assert client.post("/api/v1/customers/", CUSTOMER_PAYLOAD, format="json").status_code == 400

    no_inn = {**CUSTOMER_PAYLOAD, "inn": ""}
    assert client.post("/api/v1/customers/", no_inn, format="json").status_code == 201
    assert client.post("/api/v1/customers/", no_inn, format="json").status_code == 201


def test_delete_deactivates_and_restore_reactivates(client_for):
    customer = CustomerFactory()
    client = client_for(Role.DIRECTOR)

    assert client.delete(f"/api/v1/customers/{customer.id}/").status_code == 204
    customer.refresh_from_db()
    assert customer.is_active is False

    assert client.post(f"/api/v1/customers/{customer.id}/restore/").status_code == 200
    customer.refresh_from_db()
    assert customer.is_active is True


def test_search_by_contact_phone_has_no_duplicates(client_for):
    customer = CustomerFactory(name="Bozor")
    customer.contacts.create(full_name="A", phone="+998911111111")
    customer.contacts.create(full_name="B", phone="+998911111112")

    response = client_for(Role.DIRECTOR).get("/api/v1/customers/", {"search": "+9989111111"})
    assert response.data["count"] == 1


def test_filter_by_tag(client_for):
    CustomerFactory(tags=["vip", "toshkent"])
    CustomerFactory(tags=["yangi"])
    response = client_for(Role.DIRECTOR).get("/api/v1/customers/", {"tag": "vip"})
    assert response.data["count"] == 1


def test_accountant_can_read_but_not_write(client_for):
    client = client_for(Role.ACCOUNTANT)
    assert client.get("/api/v1/customers/").status_code == 200
    assert client.post("/api/v1/customers/", CUSTOMER_PAYLOAD, format="json").status_code == 403


@pytest.mark.parametrize("role", [Role.WAREHOUSE, Role.WORKER, Role.PRODUCTION_HEAD])
def test_unrelated_roles_have_no_access(client_for, role):
    assert client_for(role).get("/api/v1/customers/").status_code == 403


def test_cannot_add_contact_to_foreign_customer(client_for):
    foreign = CustomerFactory()
    response = client_for(Role.SALES_MANAGER).post(
        "/api/v1/contacts/",
        {"customer": foreign.id, "full_name": "Sardor", "phone": "+998901112233"},
        format="json",
    )
    assert response.status_code == 400
    assert "customer" in response.data


def test_interaction_author_is_current_user(client_for):
    client = client_for(Role.SALES_MANAGER)
    customer = CustomerFactory(manager=client.user)

    response = client.post(
        "/api/v1/interactions/",
        {"customer": customer.id, "type": "call", "body": "Yangi kolleksiyani taklif qildim"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["author"] == client.user.id


def test_customer_changes_are_audited(client_for):
    client = client_for(Role.DIRECTOR)
    customer = CustomerFactory(credit_limit=0)
    client.patch(f"/api/v1/customers/{customer.id}/", {"credit_limit": "5000"}, format="json")

    latest = Customer.history.filter(id=customer.id).latest()
    assert latest.history_user == client.user
    assert latest.credit_limit == 5000
