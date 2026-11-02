from django.db.models import Prefetch
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.users.models import Role
from common.mixins import DeactivateOnDestroyMixin
from common.permissions import RoleBasedPermission

from .models import Category, Color, ProductModel, SizeRun, Variant
from .serializers import (
    CategorySerializer,
    ColorSerializer,
    GenerateVariantsSerializer,
    ProductModelDetailSerializer,
    ProductModelSerializer,
    SizeRunSerializer,
    VariantSerializer,
)
from .services import generate_variants


class CatalogPermissionMixin:
    """Katalogni hamma ko'radi, faqat rahbariyat va ishlab chiqarish boshlig'i o'zgartiradi."""

    permission_classes = [RoleBasedPermission]
    read_roles = None
    write_roles = [Role.ADMIN, Role.DIRECTOR, Role.PRODUCTION_HEAD]


class CategoryViewSet(CatalogPermissionMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    search_fields = ("name",)
    pagination_class = None


class ColorViewSet(CatalogPermissionMixin, viewsets.ModelViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    search_fields = ("name",)
    pagination_class = None


class SizeRunViewSet(CatalogPermissionMixin, viewsets.ModelViewSet):
    queryset = SizeRun.objects.all()
    serializer_class = SizeRunSerializer
    pagination_class = None


class ProductModelViewSet(CatalogPermissionMixin, DeactivateOnDestroyMixin, viewsets.ModelViewSet):
    filterset_fields = ("category", "gender", "season", "currency", "is_active")
    search_fields = ("article", "name")
    ordering_fields = ("article", "name", "created_at", "wholesale_price")

    def get_queryset(self):
        qs = ProductModel.objects.select_related("category", "default_size_run")
        if self.action == "retrieve":
            qs = qs.prefetch_related(
                Prefetch(
                    "variants", queryset=Variant.objects.select_related("color", "product_model")
                )
            )
        return qs

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ProductModelDetailSerializer
        if self.action == "generate_variants":
            return GenerateVariantsSerializer
        return ProductModelSerializer

    @extend_schema(responses={201: VariantSerializer(many=True)})
    @action(detail=True, methods=["post"], url_path="generate-variants")
    def generate_variants(self, request, pk=None):
        product_model = self.get_object()
        serializer = GenerateVariantsSerializer(
            data=request.data, context={"request": request, "product_model": product_model}
        )
        serializer.is_valid(raise_exception=True)
        created = generate_variants(
            product_model, serializer.validated_data["colors"], serializer.validated_data["sizes"]
        )
        return Response(VariantSerializer(created, many=True).data, status=status.HTTP_201_CREATED)


class VariantViewSet(CatalogPermissionMixin, DeactivateOnDestroyMixin, viewsets.ModelViewSet):
    queryset = Variant.objects.select_related("product_model", "color")
    serializer_class = VariantSerializer
    filterset_fields = ("product_model", "color", "size", "barcode", "is_active")
    search_fields = ("product_model__article", "product_model__name", "barcode")
