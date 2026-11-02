from rest_framework.permissions import SAFE_METHODS, BasePermission


class RoleBasedPermission(BasePermission):
    """
    View'dagi atributlar bo'yicha rolni tekshiradi:
      read_roles  — GET/HEAD/OPTIONS uchun (None bo'lsa, har qanday tizimga kirgan foydalanuvchi)
      write_roles — qolgan metodlar uchun (None bo'lsa, read_roles bilan bir xil)
    Superuser hamma narsaga ruxsatga ega.
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser:
            return True

        read_roles = getattr(view, "read_roles", None)
        write_roles = getattr(view, "write_roles", read_roles)
        roles = read_roles if request.method in SAFE_METHODS else write_roles
        return roles is None or user.role in roles
