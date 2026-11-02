from rest_framework.routers import DefaultRouter

from .views import CurrencyRateViewSet, CustomerBalanceViewSet, LedgerEntryViewSet, PaymentViewSet

router = DefaultRouter()
router.register("finance/rates", CurrencyRateViewSet, basename="currency-rate")
router.register("finance/payments", PaymentViewSet, basename="payment")
router.register("finance/ledger", LedgerEntryViewSet, basename="ledger-entry")
router.register("finance/balances", CustomerBalanceViewSet, basename="customer-balance")

urlpatterns = router.urls
