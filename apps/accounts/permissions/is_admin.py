from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to users with the ADMIN role.
    """
    def has_permission(self, request, view) -> bool:
        return (
            request.user and
            request.user.is_authenticated and
            request.user.has_role('ADMIN')
        )
