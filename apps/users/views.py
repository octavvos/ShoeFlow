from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from common.permissions import RoleBasedPermission

from .models import Role, User
from .serializers import ChangePasswordSerializer, UserCreateSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.order_by("first_name", "last_name")
    permission_classes = [RoleBasedPermission]
    read_roles = [Role.ADMIN, Role.DIRECTOR]
    write_roles = [Role.ADMIN]
    filterset_fields = ("role", "is_active")
    search_fields = ("username", "first_name", "last_name", "phone")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action == "change_password":
            return ChangePasswordSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ("me", "change_password"):
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @extend_schema(responses={204: None})
    @action(detail=False, methods=["post"], url_path="me/change-password")
    def change_password(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response(status=status.HTTP_204_NO_CONTENT)
