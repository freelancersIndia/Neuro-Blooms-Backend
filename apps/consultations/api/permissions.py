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


class IsAdminOrDoctorOwnerOrReceptionistReadOnly(permissions.BasePermission):
    """
    Permissions check:
    - Super Admin & Admin: Full Access.
    - Doctor: Manage Own Schedule Only (GET/POST/PATCH/DELETE for their own schedule).
    - Receptionist: Read Only (GET, HEAD, OPTIONS).
    """
    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        # Admin gets full access
        if request.user.has_role('ADMIN') or request.user.is_superuser:
            return True

        # Receptionist gets Read-Only
        if request.user.has_role('RECEPTIONIST'):
            return request.method in permissions.SAFE_METHODS

        # Doctor gets full access to their own data (checked at object-level or view-level)
        if request.user.has_role('DOCTOR'):
            # Double check the doctor_id from the URL
            doctor_id = view.kwargs.get('doctor_id')
            if doctor_id:
                # If doctor is requesting, they must match the doctor_id in the path
                return str(request.user.id) == str(doctor_id)
            return True

        return False

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.has_role('ADMIN') or request.user.is_superuser:
            return True

        if request.user.has_role('RECEPTIONIST'):
            return request.method in permissions.SAFE_METHODS

        if request.user.has_role('DOCTOR'):
            doctor_id = None
            if hasattr(obj, 'doctor'):
                doctor_id = obj.doctor.id
            elif hasattr(obj, 'id') and obj.__class__.__name__ == 'User':
                doctor_id = obj.id

            return doctor_id is not None and str(doctor_id) == str(request.user.id)

        return False


class IsAdminOrReceptionistOrDoctorReadOnly(permissions.BasePermission):
    """
    Permissions check:
    - Super Admin & Admin: Full Access.
    - Receptionist: Full Access.
    - Doctor: Read Only (GET, HEAD, OPTIONS).
    """
    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        # Admin & Superuser get full access
        if request.user.has_role('ADMIN') or request.user.is_superuser:
            return True

        # Receptionist gets full access
        if request.user.has_role('RECEPTIONIST'):
            return True

        # Doctor gets Read-Only
        if request.user.has_role('DOCTOR'):
            return request.method in permissions.SAFE_METHODS

        return False


class IsDoctorOrAdminOrReceptionist(permissions.BasePermission):
    """
    Permissions check:
    - Doctor, Admin, Receptionist: Full Access.
    """
    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False
        return (
            request.user.has_role('ADMIN') or
            request.user.is_superuser or
            request.user.has_role('RECEPTIONIST') or
            request.user.has_role('DOCTOR')
        )


class IsDoctorWriteOrAdminOrReceptionistReadOnly(permissions.BasePermission):
    """
    Permissions check for Clinical Consultation:
    - Write (POST, PATCH, DELETE): Only Doctors.
    - Read (GET, HEAD, OPTIONS): Doctors, Admins, Receptionists.
    """
    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        # Write operations: Only Doctors
        if request.method not in permissions.SAFE_METHODS:
            return request.user.has_role('DOCTOR')

        # Read operations: Doctors, Admins, Receptionists
        return (
            request.user.has_role('ADMIN') or
            request.user.is_superuser or
            request.user.has_role('RECEPTIONIST') or
            request.user.has_role('DOCTOR')
        )


class IsAdminOrReceptionist(permissions.BasePermission):
    """
    Allows access only to users with ADMIN or RECEPTIONIST role, or superusers.
    """
    def has_permission(self, request, view) -> bool:
        return (
            request.user and
            request.user.is_authenticated and
            (
                request.user.is_superuser or
                request.user.has_role('ADMIN') or
                request.user.has_role('RECEPTIONIST')
            )
        )



