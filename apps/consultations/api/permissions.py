from rest_framework import permissions

class IsAdminOrReceptionistReadOnly(permissions.BasePermission):
    """
    Allows full access (create, update, delete) to users with the ADMIN role,
    and Read-Only access (GET, HEAD, OPTIONS) to users with the RECEPTIONIST role.
    Doctors and anonymous users are denied access.
    """
    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        # Admin gets full access (covers Super Admin as they automatically get ADMIN role in User manager)
        if request.user.has_role('ADMIN') or request.user.is_superuser:
            return True

        # Receptionist gets Read-Only access
        if request.user.has_role('RECEPTIONIST'):
            return request.method in permissions.SAFE_METHODS

        return False
