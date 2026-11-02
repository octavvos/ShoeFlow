from django.http import HttpResponse
from django.utils.text import slugify
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.customers.selectors import visible_customers
from apps.users.models import Role
from common.permissions import RoleBasedPermission

from . import services
from .exports import reconciliation_xlsx
from .filters import CustomerBalanceFilter, LedgerEntryFilter, PaymentFilter
from .models import CurrencyRate, LedgerEntry, Payment
from .selectors import customer_balances
from .serializers import (
    AdjustmentSerializer,
    CancelPaymentSerializer,
    CurrencyRateSerializer,
    CustomerBalanceSerializer,
    LedgerEntrySerializer,
    PaymentSerializer,
    ReconciliationQuerySerializer,
    ReconciliationSerializer,
)

FINANCE_WRITE_ROLES = [Role.ADMIN, Role.DIRECTOR, Role.ACCOUNTANT]
FINANCE_READ_ROLES = [*FINANCE_WRITE_ROLES, Role.SALES_MANAGER]


class FinancePermissionMixin:
    permission_classes = [RoleBasedPermission]
    read_roles = FINANCE_READ_ROLES
    write_roles = FINANCE_WRITE_ROLES


class CurrencyRateViewSet(
    FinancePermissionMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = CurrencyRate.objects.all()
    serializer_class = CurrencyRateSerializer
    read_roles = None
    filterset_fields = ("currency", "date", "source")

    @extend_schema(request=None, responses={200: CurrencyRateSerializer(many=True)})
    @action(detail=False, methods=["post"])
    def fetch(self, request):
        """Markaziy bank kursini hozir olish (odatda Celery har kuni o'zi oladi)."""
        return Response(CurrencyRateSerializer(services.fetch_cbu_rates(), many=True).data)


class PaymentViewSet(
    FinancePermissionMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """To'lovlar o'zgartirilmaydi va o'chirilmaydi — faqat bekor qilinadi."""

    serializer_class = PaymentSerializer
    filterset_class = PaymentFilter
    search_fields = ("customer__name", "comment")
    ordering_fields = ("paid_at", "amount", "created_at")

    def get_queryset(self):
        return Payment.objects.select_related("customer", "created_by").filter(
            customer__in=visible_customers(self.request.user)
        )

    def perform_create(self, serializer):
        serializer.instance = services.register_payment(
            user=self.request.user, **serializer.validated_data
        )

    @extend_schema(request=CancelPaymentSerializer, responses={200: PaymentSerializer})
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = CancelPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = services.cancel_payment(
            self.get_object(), user=request.user, reason=serializer.validated_data["reason"]
        )
        return Response(self.get_serializer(payment).data)


class LedgerEntryViewSet(FinancePermissionMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = LedgerEntrySerializer
    filterset_class = LedgerEntryFilter
    ordering_fields = ("date", "amount")

    def get_queryset(self):
        return (
            LedgerEntry.objects.select_related("customer")
            .filter(customer__in=visible_customers(self.request.user))
            .order_by("-date", "-id")
        )

    @extend_schema(request=AdjustmentSerializer, responses={201: LedgerEntrySerializer})
    @action(detail=False, methods=["post"])
    def adjustment(self, request):
        """Qo'lda tuzatish yoki eski tizimdan o'tkazilgan boshlang'ich qoldiq."""
        serializer = AdjustmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        entry = services.add_adjustment(
            data["customer"],
            data["amount"],
            user=request.user,
            description=data["description"],
            entry_date=data.get("date"),
            opening=data["opening"],
        )
        return Response(LedgerEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class CustomerBalanceViewSet(FinancePermissionMixin, viewsets.ReadOnlyModelViewSet):
    """Mijozlar balansi: qarz, ochiq buyurtmalar, bo'sh kredit limiti."""

    serializer_class = CustomerBalanceSerializer
    filterset_class = CustomerBalanceFilter
    search_fields = ("name", "phone")
    ordering_fields = ("balance", "available_credit", "credit_limit", "last_payment_date", "name")
    ordering = ("-balance",)

    def get_queryset(self):
        return customer_balances(self.request.user)

    @extend_schema(
        parameters=[ReconciliationQuerySerializer],
        responses={
            200: OpenApiResponse(
                ReconciliationSerializer, description="export=xlsx bo'lsa — Excel fayl"
            )
        },
    )
    @action(detail=True, methods=["get"])
    def reconciliation(self, request, pk=None):
        """Akt-sverka: berilgan davr uchun boshlang'ich qoldiq, harakatlar va yakuniy qoldiq."""
        query = ReconciliationQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = query.validated_data
        rec = services.reconciliation(self.get_object(), params["date_from"], params["date_to"])

        if params.get("export") == "xlsx":
            filename = (
                f"akt-sverka-{slugify(rec.customer.name) or rec.customer.pk}-{rec.date_to}.xlsx"
            )
            return HttpResponse(
                reconciliation_xlsx(rec),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        return Response(ReconciliationSerializer(rec).data)
