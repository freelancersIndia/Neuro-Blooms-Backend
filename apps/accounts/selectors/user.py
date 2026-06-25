from django.db.models import QuerySet, Q, Value, CharField, Count
from django.db.models.functions import Concat
from apps.accounts.models.user import User
from apps.accounts.filters.user import UserFilter

def get_users_queryset(filters: dict = None) -> QuerySet:
    """
    Returns an optimized, filtered, and sorted queryset of users.
    """
    queryset = User.objects.all()
    
    # Optimize query by prefetching roles (avoid N+1 queries)
    queryset = queryset.prefetch_related('roles')
    
    if filters:
        # Apply role and is_active filters
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
            
    # Default sorting: Newest users first (-created_at)
    queryset = queryset.order_by('-created_at')
    
    return queryset

def get_user_statistics() -> dict:
    """
    Computes dashboard summary statistics using efficient database aggregation.
    """
    stats = User.objects.aggregate(
        total_users=Count('id'),
        verified_users=Count('id', filter=Q(is_verified=True)),
        active_users=Count('id', filter=Q(is_active=True)),
        inactive_users=Count('id', filter=Q(is_active=False))
    )
    return {
        "total_users": stats["total_users"] or 0,
        "verified_users": stats["verified_users"] or 0,
        "active_users": stats["active_users"] or 0,
        "inactive_users": stats["inactive_users"] or 0,
    }

from django.core.exceptions import ValidationError

def get_user_by_id(user_id) -> User:
    """
    Retrieves a user by ID, optimized with prefetch_related for roles and locks to prevent N+1 queries.
    """
    try:
        return User.objects.prefetch_related('roles', 'locks').get(id=user_id)
    except (User.DoesNotExist, ValidationError, ValueError):
        return None
