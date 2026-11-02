import pytest
from django.core.exceptions import ValidationError

from apps.catalog.models import Variant
from apps.catalog.services import generate_variants
from apps.users.models import Role
from common.validators import ean13_check_digit, validate_ean13

from .factories import ColorFactory, ProductModelFactory, SizeRunFactory


def test_ean13_check_digit():
    # Vikipediyadagi klassik misol: 4006381333931
    assert ean13_check_digit("400638133393") == "1"
    validate_ean13("4006381333931")
    with pytest.raises(ValidationError):
        validate_ean13("4006381333932")


@pytest.mark.django_db
class TestVariants:
    def test_variant_gets_valid_internal_barcode(self):
        variant = Variant.objects.create(
            product_model=ProductModelFactory(), color=ColorFactory(), size=40
        )
        assert variant.barcode.startswith("200")
        validate_ean13(variant.barcode)
        variant.refresh_from_db()
        assert variant.barcode is not None

    def test_generate_variants_skips_existing(self):
        model = ProductModelFactory()
        black, brown = ColorFactory(name="Qora"), ColorFactory(name="Jigarrang")
        Variant.objects.create(product_model=model, color=black, size=40)

        created = generate_variants(model, [black, brown], [40, 41, 41, 42])

        assert len(created) == 5  # 2 rang x 3 razmer - 1 mavjud
        assert model.variants.count() == 6

    def test_generate_variants_endpoint_uses_default_size_run(self, client_for):
        model = ProductModelFactory(default_size_run=SizeRunFactory())
        color = ColorFactory(name="Qora")

        response = client_for(Role.PRODUCTION_HEAD).post(
            f"/api/v1/product-models/{model.id}/generate-variants/",
            {"colors": [color.id]},
            format="json",
        )
        assert response.status_code == 201
        assert [v["size"] for v in response.data] == [39, 40, 41, 42, 43, 44]

    def test_generate_variants_requires_sizes_or_size_run(self, client_for):
        model = ProductModelFactory()
        response = client_for(Role.ADMIN).post(
            f"/api/v1/product-models/{model.id}/generate-variants/",
            {"colors": [ColorFactory().id]},
            format="json",
        )
        assert response.status_code == 400

    def test_lookup_variant_by_barcode(self, client_for):
        variant = Variant.objects.create(
            product_model=ProductModelFactory(), color=ColorFactory(), size=41
        )
        response = client_for(Role.WAREHOUSE).get("/api/v1/variants/", {"barcode": variant.barcode})
        assert response.data["count"] == 1
        assert response.data["results"][0]["article"] == variant.product_model.article


@pytest.mark.django_db
class TestPermissions:
    def test_everyone_can_read_catalog(self, client_for):
        ProductModelFactory()
        assert client_for(Role.WORKER).get("/api/v1/product-models/").status_code == 200

    def test_sales_manager_cannot_change_catalog(self, client_for):
        model = ProductModelFactory()
        response = client_for(Role.SALES_MANAGER).patch(
            f"/api/v1/product-models/{model.id}/", {"name": "Boshqa"}, format="json"
        )
        assert response.status_code == 403


@pytest.mark.django_db
class TestSizeRun:
    def test_size_run_is_sorted_and_counted(self, client_for):
        response = client_for(Role.ADMIN).post(
            "/api/v1/size-runs/",
            {"name": "Ayollar 36-40", "sizes": {"38": 2, "36": 1, "37": 2, "39": 1, "40": 1}},
            format="json",
        )
        assert response.status_code == 201
        assert list(response.data["sizes"]) == ["36", "37", "38", "39", "40"]
        assert response.data["total_pairs"] == 7

    @pytest.mark.parametrize("sizes", [{}, {"99": 1}, {"40": 0}, {"40": "2"}, ["40"]])
    def test_invalid_size_run_rejected(self, client_for, sizes):
        response = client_for(Role.ADMIN).post(
            "/api/v1/size-runs/", {"name": "Xato", "sizes": sizes}, format="json"
        )
        assert response.status_code == 400


@pytest.mark.django_db
def test_negative_price_rejected(client_for):
    model = ProductModelFactory()
    response = client_for(Role.ADMIN).patch(
        f"/api/v1/product-models/{model.id}/", {"retail_price": "-5"}, format="json"
    )
    assert response.status_code == 400
