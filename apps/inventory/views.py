from django.db.models import F
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.models import Role
from common.mixins import DeactivateOnDestroyMixin
from common.permissions import RoleBasedPermission

from . import services
from .filters import StockBalanceFilter, StockMovementFilter
from .models import StockBalance, StockMovement, Warehouse
from .serializers import (
    AdjustSerializer,
    ReceiveSerializer,
    StockBalanceSerializer,
    StockMovementSerializer,
    TransferSerializer,
    WarehouseSerializer,
    WriteOffSerializer,
)

STOCK_READ_ROLES = [
    Role.ADMIN,
    Role.DIRECTOR,
    Role.WAREHOUSE,
    Role.SALES_MANAGER,
    Role.PRODUCTION_HEAD,
    Role.ACCOUNTANT,
]
STOCK_WRITE_ROLES = [Role.ADMIN, Role.DIRECTOR, Role.WAREHOUSE]


class WarehouseViewSet(DeactivateOnDestroyMixin, viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [RoleBasedPermission]
    read_roles = STOCK_READ_ROLES
    write_roles = [Role.ADMIN, Role.DIRECTOR]
    filterset_fields = ("is_active",)
    search_fields = ("name",)
    pagination_class = None


class StockBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StockBalanceSerializer
    permission_classes = [RoleBasedPermission]
    read_roles = STOCK_READ_ROLES
    filterset_class = StockBalanceFilter
    search_fields = (
        "variant__product_model__article",
        "variant__product_model__name",
        "variant__barcode",
    )
    ordering_fields = ("quantity", "reserved", "available_qty", "variant__size")
    ordering = ("variant__product_model__article", "variant__color__name", "variant__size")

    def get_queryset(self):
        return StockBalance.objects.select_related(
            "warehouse", "variant__product_model", "variant__color"
        ).annotate(available_qty=F("quantity") - F("reserved"))


class StockMovementViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Harakatlar jurnali faqat o'qiladi; yangi harakatlar quyidagi action'lar orqali yaratiladi."""

    queryset = StockMovement.objects.select_related(
        "warehouse", "variant__product_model", "variant__color", "created_by"
    )
    serializer_class = StockMovementSerializer
    permission_classes = [RoleBasedPermission]
    read_roles = STOCK_READ_ROLES
    write_roles = STOCK_WRITE_ROLES
    filterset_class = StockMovementFilter
    search_fields = ("variant__product_model__article", "variant__barcode", "reference", "comment")

    def _created(self, movements):
        return Response(
            StockMovementSerializer(movements, many=True).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(request=ReceiveSerializer, responses={201: StockMovementSerializer(many=True)})
    @action(detail=False, methods=["post"])
    def receive(self, request):
        data = self._validated(ReceiveSerializer)
        movements = services.receive(
            data["warehouse"],
            data["items"],
            user=request.user,
            reference=data.get("reference", ""),
            comment=data.get("comment", ""),
        )
        return self._created(movements)

    @extend_schema(request=WriteOffSerializer, responses={201: StockMovementSerializer(many=True)})
    @action(detail=False, methods=["post"], url_path="write-off")
    def write_off(self, request):
        data = self._validated(WriteOffSerializer)
        movements = services.write_off(
            data["warehouse"], data["items"], user=request.user, comment=data["comment"]
        )
        return self._created(movements)

    @extend_schema(request=TransferSerializer, responses={201: StockMovementSerializer(many=True)})
    @action(detail=False, methods=["post"])
    def transfer(self, request):
        data = self._validated(TransferSerializer)
        movements = services.transfer(
            data["source"],
            data["target"],
            data["items"],
            user=request.user,
            comment=data.get("comment", ""),
        )
        return self._created(movements)

    @extend_schema(request=AdjustSerializer, responses={201: StockMovementSerializer(many=True)})
    @action(detail=False, methods=["post"])
    def adjust(self, request):
        data = self._validated(AdjustSerializer)
        movement = services.adjust(
            data["warehouse"],
            data["variant"],
            data["counted"],
            user=request.user,
            comment=data.get("comment", ""),
        )
        return self._created([movement] if movement else [])

    def _validated(self, serializer_class):
        serializer = serializer_class(data=self.request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data
