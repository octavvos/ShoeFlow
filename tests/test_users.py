import pytest

from apps.users.models import Role, User

from .factories import UserFactory

pytestmark = pytest.mark.django_db


def test_obtain_jwt_token(api_client):
    UserFactory(username="ali")
    response = api_client.post(
        "/api/v1/auth/token/", {"username": "ali", "password": "Parol-12345"}, format="json"
    )
    assert response.status_code == 200
    assert {"access", "refresh"} <= response.data.keys()


def test_me_returns_current_user(client_for):
    client = client_for(Role.WORKER)
    response = client.get("/api/v1/users/me/")
    assert response.status_code == 200
    assert response.data["role"] == Role.WORKER


def test_anonymous_is_rejected(api_client):
    assert api_client.get("/api/v1/users/me/").status_code == 401


def test_admin_creates_user_with_hashed_password(client_for):
    response = client_for(Role.ADMIN).post(
        "/api/v1/users/",
        {"username": "vali", "password": "Murakkab-parol-1", "role": Role.WAREHOUSE},
        format="json",
    )
    assert response.status_code == 201
    assert "password" not in response.data
    assert User.objects.get(username="vali").check_password("Murakkab-parol-1")


def test_weak_password_rejected(client_for):
    response = client_for(Role.ADMIN).post(
        "/api/v1/users/", {"username": "vali", "password": "123"}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize("role", [Role.DIRECTOR, Role.SALES_MANAGER, Role.WORKER])
def test_non_admin_cannot_create_users(client_for, role):
    response = client_for(role).post(
        "/api/v1/users/", {"username": "x", "password": "Murakkab-parol-1"}, format="json"
    )
    assert response.status_code == 403


def test_change_password(client_for):
    client = client_for(Role.WORKER)
    response = client.post(
        "/api/v1/users/me/change-password/",
        {"old_password": "Parol-12345", "new_password": "Yangi-parol-777"},
        format="json",
    )
    assert response.status_code == 204
    client.user.refresh_from_db()
    assert client.user.check_password("Yangi-parol-777")


def test_superuser_gets_admin_role():
    user = User.objects.create_superuser("boss", password="x")
    assert user.role == Role.ADMIN
