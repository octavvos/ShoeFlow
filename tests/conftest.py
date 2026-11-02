import pytest
from rest_framework.test import APIClient

from apps.users.models import Role

from .factories import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def client_for(db):
    """Berilgan rol (yoki foydalanuvchi) bilan autentifikatsiya qilingan APIClient qaytaradi."""

    def make(role_or_user=Role.ADMIN):
        user = role_or_user if hasattr(role_or_user, "pk") else UserFactory(role=role_or_user)
        client = APIClient()
        client.force_authenticate(user)
        client.user = user
        return client

    return make
