from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.models import Role
from common.permissions import RoleBasedPermission

from . import services
from .filters import OrderFilter
from .models import OrderItem
from .selectors import visible_orders
from .serializers import (
    AddBoxesSerializer,
    AddItemSerializer,
    OrderDetailSerializer,
    OrderSerializer,
    UpdateItemSerializer,
)

SALES_ROLES = [Role.ADMIN, Role.DIRECTOR, Role.SALES_MANAGER]
SHIPPING_ROLES = [Role.ADMIN, Role.DIRECTOR, Role.WAREHOUSE]


class OrderViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleBasedPermission]
    read_roles = [*SALES_ROLES, Role.WAREHOUSE, Role.ACCOUNTANT]
    write_roles = SALES_ROLES
    action_roles = {"ship": SHIPPING_ROLES, "deliver": SHIPPING_ROLES}
    filterset_class = OrderFilter
    search_fields = ("customer__name", "customer__phone", "comment")
    ordering_fields = ("created_at", "total_amount", "status")
    # PUT yo'q: buyurtma faqat PATCH bilan qisman yangilanadi
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = visible_orders(self.request.user)
        if self.action != "list":
            qs = qs.prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.select_related(
                        "variant__product_model", "variant__color"
                    ),
                )
            )
        return qs

    def get_serializer_class(self):
        return OrderSerializer if self.action == "list" else OrderDetailSerializer

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Buyurtma o'chirilmaydi, uni bekor qiling (POST .../cancel/)."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def _detail(self, order, status_code=status.HTTP_200_OK):
        fresh = self.get_queryset().get(pk=order.pk)
        return Response(
            OrderDetailSerializer(fresh, context=self.get_serializer_context()).data,
            status=status_code,
        )

    def _validated(self, serializer_class, **kwargs):
        serializer = serializer_class(
            data=self.request.data, context=self.get_serializer_context(), **kwargs
        )
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return self._detail(serializer.save(), status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_object(), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return self._detail(serializer.save())

    @extend_schema(request=AddItemSerializer, responses={201: OrderDetailSerializer})
    @action(detail=True, methods=["post"])
    def items(self, request, pk=None):
        order = self.get_object()
        services.add_item(order, **self._validated(AddItemSerializer))
        return self._detail(order, status.HTTP_201_CREATED)

    @extend_schema(request=UpdateItemSerializer, responses={200: OrderDetailSerializer})
    @action(detail=True, methods=["patch", "delete"], url_path=r"items/(?P<item_id>\d+)")
    def item(self, request, pk=None, item_id=None):
        order = self.get_object()
        item = get_object_or_404(order.items, pk=item_id)
        if request.method == "DELETE":
            services.remove_item(item)
        else:
            services.update_item(item, **self._validated(UpdateItemSerializer))
        return self._detail(order)

    @extend_schema(request=AddBoxesSerializer, responses={201: OrderDetailSerializer})
    @action(detail=True, methods=["post"])
    def boxes(self, request, pk=None):
        order = self.get_object()
        services.add_boxes(order, **self._validated(AddBoxesSerializer))
        return self._detail(order, status.HTTP_201_CREATED)

    @extend_schema(request=None, responses={200: OrderDetailSerializer})
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self._detail(services.confirm_order(self.get_object(), user=request.user))

    @extend_schema(request=None, responses={200: OrderDetailSerializer})
    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        return self._detail(services.ship_order(self.get_object(), user=request.user))

    @extend_schema(request=None, responses={200: OrderDetailSerializer})
    @action(detail=True, methods=["post"])
    def deliver(self, request, pk=None):
        return self._detail(services.deliver_order(self.get_object(), user=request.user))

    @extend_schema(request=None, responses={200: OrderDetailSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._detail(services.cancel_order(self.get_object(), user=request.user))
