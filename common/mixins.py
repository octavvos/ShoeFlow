from rest_framework.decorators import action
from rest_framework.response import Response


class DeactivateOnDestroyMixin:
    """
    DELETE yozuvni bazadan o'chirmaydi, faqat is_active=False qiladi
    (buyurtma, to'lov va boshqa tarix saqlanib qolishi uchun).
    POST {id}/restore/ esa qayta faollashtiradi.
    """

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        instance = self.get_object()
        instance.is_active = True
        instance.save(update_fields=["is_active", "updated_at"])
        return Response(self.get_serializer(instance).data)
