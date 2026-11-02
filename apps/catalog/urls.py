from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    ColorViewSet,
    ProductModelViewSet,
    SizeRunViewSet,
    VariantViewSet,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("colors", ColorViewSet, basename="color")
router.register("size-runs", SizeRunViewSet, basename="size-run")
router.register("product-models", ProductModelViewSet, basename="product-model")
router.register("variants", VariantViewSet, basename="variant")

urlpatterns = router.urls
