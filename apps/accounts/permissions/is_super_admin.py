from rest_framework import permissions

class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to superusers or users with the ADMIN role.
    """
    def has_permission(self, request, view) -> bool:
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or request.user.has_role('ADMIN'))
        )
