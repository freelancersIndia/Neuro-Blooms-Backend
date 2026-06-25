from rest_framework.exceptions import ValidationError
from django.db.models import QuerySet
from apps.accounts.constants.roles import SystemRole

class UserFilter:
    """
    Filter class for User queries to filter by active status and role name.
    """
    def __init__(self, params: dict):
        self.params = params or {}

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        # 1. Status Filter (?is_active=true/false)
        is_active_query = self.params.get('is_active')
        if is_active_query is not None:
            if isinstance(is_active_query, bool):
                queryset = queryset.filter(is_active=is_active_query)
            elif isinstance(is_active_query, str):
                is_active_clean = is_active_query.strip().lower()
                if is_active_clean in ('true', '1', 't'):
                    queryset = queryset.filter(is_active=True)
                elif is_active_clean in ('false', '0', 'f'):
                    queryset = queryset.filter(is_active=False)
                else:
                    raise ValidationError({'is_active': ["Must be a valid boolean value ('true' or 'false')."]})
            else:
                # Handle potential other types like int
                if is_active_query in (True, 1):
                    queryset = queryset.filter(is_active=True)
                elif is_active_query in (False, 0):
                    queryset = queryset.filter(is_active=False)
                else:
                    raise ValidationError({'is_active': ["Must be a valid boolean value ('true' or 'false')."]})

        # 2. Role Filter (?role=...)
        role_query = self.params.get('role')
        if role_query is not None:
            if isinstance(role_query, str):
                role_query_clean = role_query.strip().upper()
                valid_roles = [r.upper() for r in SystemRole.ALL]
                if role_query_clean in valid_roles:
                    queryset = queryset.filter(roles__name=role_query_clean)
                else:
                    # Ignore invalid role names by returning an empty result set (do not raise a server error)
                    queryset = queryset.none()
            else:
                queryset = queryset.none()

        return queryset
