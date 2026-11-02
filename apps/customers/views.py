from rest_framework import viewsets

from apps.users.models import Role
from common.mixins import DeactivateOnDestroyMixin
from common.permissions import RoleBasedPermission

from .filters import CustomerFilter
from .models import Contact, Interaction
from .selectors import visible_customers
from .serializers import (
    ContactSerializer,
    CustomerDetailSerializer,
    CustomerSerializer,
    InteractionSerializer,
)

CUSTOMER_WRITE_ROLES = [Role.ADMIN, Role.DIRECTOR, Role.SALES_MANAGER]
CUSTOMER_READ_ROLES = [*CUSTOMER_WRITE_ROLES, Role.ACCOUNTANT]


class CustomerScopedMixin:
    permission_classes = [RoleBasedPermission]
    read_roles = CUSTOMER_READ_ROLES
    write_roles = CUSTOMER_WRITE_ROLES


class CustomerViewSet(DeactivateOnDestroyMixin, CustomerScopedMixin, viewsets.ModelViewSet):
    filterset_class = CustomerFilter
    search_fields = ("name", "phone", "extra_phone", "inn", "contacts__phone")
    ordering_fields = ("name", "created_at", "credit_limit")

    def get_queryset(self):
        qs = visible_customers(self.request.user)
        if self.action == "retrieve":
            qs = qs.prefetch_related("contacts")
        return qs

    def get_serializer_class(self):
        return CustomerDetailSerializer if self.action == "retrieve" else CustomerSerializer

    def _save(self, serializer):
        user = self.request.user
        # Savdo menejeri mijozni faqat o'ziga biriktira oladi
        if user.role == Role.SALES_MANAGER and not user.is_superuser:
            serializer.save(manager=user)
        else:
            serializer.save()

    perform_create = _save
    perform_update = _save


class ContactViewSet(CustomerScopedMixin, viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    filterset_fields = ("customer",)
    search_fields = ("full_name", "phone")

    def get_queryset(self):
        return Contact.objects.filter(customer__in=visible_customers(self.request.user))


class InteractionViewSet(CustomerScopedMixin, viewsets.ModelViewSet):
    serializer_class = InteractionSerializer
    filterset_fields = ("customer", "type", "author")
    ordering_fields = ("occurred_at",)

    def get_queryset(self):
        return Interaction.objects.select_related("author").filter(
            customer__in=visible_customers(self.request.user)
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
