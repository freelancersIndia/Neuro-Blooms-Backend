from rest_framework import permissions

class IsAdminOrReceptionist(permissions.BasePermission):
    """
    Allows access only to authenticated users with ADMIN or RECEPTIONIST roles.
    DOCTOR role or other roles will be forbidden.
    """
    def has_permission(self, request, view) -> bool:
        return (
            request.user and
            request.user.is_authenticated and
            request.user.has_any_role(['ADMIN', 'RECEPTIONIST'])
        )

class IsAdminOrReceptionistOrDoctor(permissions.BasePermission):
    """
    Allows access to authenticated users with ADMIN, RECEPTIONIST, or DOCTOR roles.
    """
    def has_permission(self, request, view) -> bool:
        return (
            request.user and
            request.user.is_authenticated and
            request.user.has_any_role(['ADMIN', 'RECEPTIONIST', 'DOCTOR'])
        )
