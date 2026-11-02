from rest_framework.routers import DefaultRouter

from .views import ContactViewSet, CustomerViewSet, InteractionViewSet

router = DefaultRouter()
router.register("customers", CustomerViewSet, basename="customer")
router.register("contacts", ContactViewSet, basename="contact")
router.register("interactions", InteractionViewSet, basename="interaction")

urlpatterns = router.urls
