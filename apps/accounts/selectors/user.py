from django.db.models import QuerySet, Q, Value, CharField, Count, OuterRef, Subquery, Exists
from django.db.models.functions import Concat, Coalesce
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models.user import User, FailedLoginAttempt, AccountLock
from apps.accounts.filters.user import UserFilter

def get_users_queryset(filters: dict = None) -> QuerySet:
    """
    Returns an optimized, filtered, and sorted queryset of users.
    """
    queryset = User.objects.filter(is_deleted=False)
    
    # Optimize query by prefetching roles (avoid N+1 queries)
    queryset = queryset.prefetch_related('roles')
    
    # Annotate failed_login_attempts_count using a subquery to avoid N+1 queries
    failed_attempts_subquery = FailedLoginAttempt.objects.filter(
        email=OuterRef('email')
    ).values('email').annotate(
        cnt=Count('id')
    ).values('cnt')
    
    # Annotate is_locked_annotated (true if there's an active lock)
    active_locks = AccountLock.objects.filter(
        user=OuterRef('pk'),
        is_active=True,
        unlock_at__gt=timezone.now()
    )
    
    queryset = queryset.annotate(
        failed_login_attempts_count=Coalesce(Subquery(failed_attempts_subquery), Value(0)),
        is_locked_annotated=Exists(active_locks)
    )
    
    if filters:
        # Apply role, active, blocked, locked, and date filters
        filter_handler = UserFilter(filters)
        queryset = filter_handler.filter_queryset(queryset)
        
        # Apply search query
        search_query = filters.get('search')
        if search_query:
            search_query = search_query.strip()
            # Annotate full_name to support simultaneous case-insensitive search
            queryset = queryset.annotate(
                full_name=Concat('first_name', Value(' '), 'last_name', output_field=CharField())
            ).filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(full_name__icontains=search_query)
            )
            
    # Apply ordering
    ordering = filters.get('ordering') if filters else None
    if ordering:
        ordering_map = {
            'name': ('first_name', 'last_name'),
            '-name': ('-first_name', '-last_name'),
            'created_date': ('created_at',),
            '-created_date': ('-created_at',),
            'created_at': ('created_at',),
            '-created_at': ('-created_at',),
            'updated_date': ('updated_at',),
            '-updated_date': ('-updated_at',),
            'updated_at': ('updated_at',),
            '-updated_at': ('-updated_at',),
            'last_login': ('last_login',),
            '-last_login': ('-last_login',),
            'failed_attempts': ('failed_login_attempts_count',),
            '-failed_attempts': ('-failed_login_attempts_count',),
            'email': ('email',),
            '-email': ('-email',),
        }
        fields = ordering_map.get(ordering)
        if fields:
            queryset = queryset.order_by(*fields)
        else:
            queryset = queryset.order_by('-created_at')
    else:
        # Default sorting: Newest users first (-created_at)
        queryset = queryset.order_by('-created_at')
    
    return queryset

def get_user_statistics() -> dict:
    """
    Computes dashboard summary statistics using efficient database aggregation.
    """
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    
    # Exclude soft-deleted users from statistics
    qs = User.objects.filter(is_deleted=False)
    
    stats = qs.aggregate(
        total_users=Count('id'),
        active_users=Count('id', filter=Q(is_active=True)),
        inactive_users=Count('id', filter=Q(is_active=False)),
        verified_users=Count('id', filter=Q(is_verified=True)),
        unverified_users=Count('id', filter=Q(is_verified=False)),
        admins=Count('id', distinct=True, filter=Q(roles__name='ADMIN')),
        doctors=Count('id', distinct=True, filter=Q(roles__name='DOCTOR')),
        receptionists=Count('id', distinct=True, filter=Q(roles__name='RECEPTIONIST')),
        super_admins=Count('id', filter=Q(is_superuser=True)),
        new_users=Count('id', filter=Q(created_at__gte=seven_days_ago))
    )
    
    # Calculate locked users (manually blocked or currently locked out)
    locked_users_count = qs.filter(
        Q(is_blocked=True) | Q(locks__is_active=True, locks__unlock_at__gt=now)
    ).distinct().count()
    
    return {
        "total_users": stats["total_users"] or 0,
        "active_users": stats["active_users"] or 0,
        "inactive_users": stats["inactive_users"] or 0,
        "verified_users": stats["verified_users"] or 0,
        "unverified_users": stats["unverified_users"] or 0,
        "locked_users": locked_users_count,
        "admins": stats["admins"] or 0,
        "doctors": stats["doctors"] or 0,
        "receptionists": stats["receptionists"] or 0,
        "super_admins": stats["super_admins"] or 0,
        "new_users": stats["new_users"] or 0
    }

from django.core.exceptions import ValidationError

def get_user_by_id(user_id) -> User:
    """
    Retrieves a user by ID, optimized with prefetch_related for roles and locks to prevent N+1 queries.
    """
    try:
        return User.objects.prefetch_related('roles', 'locks').get(id=user_id, is_deleted=False)
    except (User.DoesNotExist, ValidationError, ValueError):
        return None
