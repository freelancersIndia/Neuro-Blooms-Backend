from rest_framework.exceptions import ValidationError
from django.db.models import QuerySet, Q
from django.utils import timezone
from datetime import timedelta

class UserFilter:
    """
    Filter class for User queries supporting enterprise filtering criteria.
    """
    def __init__(self, params: dict):
        self.params = params or {}

    def filter_queryset(self, queryset: QuerySet) -> QuerySet:
        # 1. Active Filter (?active=true/false)
        active_query = self.params.get('active') or self.params.get('is_active')
        if active_query is not None:
            if str(active_query).lower() in ('true', '1', 't', 'yes'):
                queryset = queryset.filter(is_active=True)
            elif str(active_query).lower() in ('false', '0', 'f', 'no'):
                queryset = queryset.filter(is_active=False)
            else:
                raise ValidationError({'is_active': ["Must be a valid boolean value ('true' or 'false')."]})

        # 2. Verified Filter (?verified=true/false)
        verified_query = self.params.get('verified') or self.params.get('is_verified')
        if verified_query is not None:
            if str(verified_query).lower() in ('true', '1', 't', 'yes'):
                queryset = queryset.filter(is_verified=True)
            elif str(verified_query).lower() in ('false', '0', 'f', 'no'):
                queryset = queryset.filter(is_verified=False)
            else:
                raise ValidationError({'is_verified': ["Must be a valid boolean value ('true' or 'false')."]})

        # 3. Blocked Filter (?blocked=true/false)
        blocked_query = self.params.get('blocked') or self.params.get('is_blocked')
        if blocked_query is not None:
            if str(blocked_query).lower() in ('true', '1', 't', 'yes'):
                queryset = queryset.filter(is_blocked=True)
            elif str(blocked_query).lower() in ('false', '0', 'f', 'no'):
                queryset = queryset.filter(is_blocked=False)
            else:
                raise ValidationError({'is_blocked': ["Must be a valid boolean value ('true' or 'false')."]})

        # 4. Locked Filter (?locked=true/false)
        # Note: requires the queryset to be annotated with `is_locked_annotated`
        locked_query = self.params.get('locked')
        if locked_query is not None:
            if str(locked_query).lower() in ('true', '1', 't', 'yes'):
                queryset = queryset.filter(is_locked_annotated=True)
            elif str(locked_query).lower() in ('false', '0', 'f', 'no'):
                queryset = queryset.filter(is_locked_annotated=False)
            else:
                raise ValidationError({'locked': ["Must be a valid boolean value ('true' or 'false')."]})

        # 5. Role Filter (Supports comma-separated or multiple role params)
        role_queries = []
        raw_roles = self.params.getlist('role') if hasattr(self.params, 'getlist') else self.params.get('role')
        if raw_roles:
            if isinstance(raw_roles, list):
                for r in raw_roles:
                    role_queries.extend([x.strip().upper() for x in r.split(',') if x.strip()])
            elif isinstance(raw_roles, str):
                role_queries.extend([x.strip().upper() for x in raw_roles.split(',') if x.strip()])
        if role_queries:
            queryset = queryset.filter(roles__name__in=role_queries).distinct()

        # 6. Date Filters (?created_after=... & ?created_before=...)
        created_after = self.params.get('created_after')
        if created_after:
            queryset = queryset.filter(created_at__gte=created_after)
        
        created_before = self.params.get('created_before')
        if created_before:
            queryset = queryset.filter(created_at__lte=created_before)

        # 7. Date Range Shortcuts (?date_range=today/7_days/30_days)
        date_range = self.params.get('date_range')
        if date_range:
            today = timezone.now().date()
            if date_range == 'today':
                queryset = queryset.filter(created_at__date=today)
            elif date_range in ('7_days', 'last_7_days', '7_days'):
                queryset = queryset.filter(created_at__date__gte=today - timedelta(days=7))
            elif date_range in ('30_days', 'last_30_days', '30_days'):
                queryset = queryset.filter(created_at__date__gte=today - timedelta(days=30))

        # 8. Profile Image Filter (?has_profile_image=yes/no)
        has_profile_image = self.params.get('has_profile_image')
        if has_profile_image is not None:
            val = str(has_profile_image).lower()
            if val in ('true', '1', 'yes'):
                queryset = queryset.exclude(profile_image='').exclude(profile_image__isnull=True)
            elif val in ('false', '0', 'no'):
                queryset = queryset.filter(Q(profile_image='') | Q(profile_image__isnull=True))

        return queryset
