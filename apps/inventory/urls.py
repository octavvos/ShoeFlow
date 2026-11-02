from rest_framework.routers import DefaultRouter

from .views import StockBalanceViewSet, StockMovementViewSet, WarehouseViewSet

router = DefaultRouter()
router.register("warehouses", WarehouseViewSet, basename="warehouse")
router.register("stock", StockBalanceViewSet, basename="stock")
router.register("stock-movements", StockMovementViewSet, basename="stock-movement")

urlpatterns = router.urls
