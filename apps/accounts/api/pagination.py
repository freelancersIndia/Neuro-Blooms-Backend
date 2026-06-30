from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError
from apps.accounts.utils.responses import success_response

class StandardPageNumberPagination(PageNumberPagination):
    """
    Standard pagination class returning responses in the custom envelope.
    """
    page_size = 20
    max_page_size = 100
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        view = self.request.parser_context.get('view') if self.request else None
        message = getattr(view, 'pagination_message', 'Data retrieved successfully.')
        
        return success_response(
            message=message,
            data={
                'count': self.page.paginator.count,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data
            }
        )


class UserAdminPagination(PageNumberPagination):
    """
    Custom pagination class for Admin User List API.
    """
    page_size = 12
    max_page_size = 100
    page_size_query_param = 'page_size'

    def paginate_queryset(self, queryset, request, view=None):
        page = request.query_params.get(self.page_query_param, 1)
        page_size = request.query_params.get(self.page_size_query_param)

        # Validate page parameter
        if page is not None:
            try:
                page_int = int(page)
                if page_int <= 0:
                    raise ValidationError({'page': ['Page number must be greater than 0.']})
            except (ValueError, TypeError):
                raise ValidationError({'page': ['Page number must be a valid integer.']})

        # Validate page_size parameter
        if page_size is not None:
            try:
                page_size_int = int(page_size)
                if page_size_int <= 0:
                    raise ValidationError({'page_size': ['Page size must be greater than 0.']})
            except (ValueError, TypeError):
                raise ValidationError({'page_size': ['Page size must be a valid integer.']})

        try:
            return super().paginate_queryset(queryset, request, view)
        except Exception as exc:
            raise ValidationError({'page': [str(exc)]})

    def get_paginated_response(self, data):
        view = self.request.parser_context.get('view') if self.request else None
        message = getattr(view, 'pagination_message', 'Users retrieved successfully.')
        
        total_pages = self.page.paginator.num_pages if self.page else 0
        current_page = self.page.number if self.page else 1
        page_size = self.get_page_size(self.request)
        
        return success_response(
            message=message,
            data={
                'count': self.page.paginator.count,
                'page': current_page,
                'page_size': page_size,
                'total_pages': total_pages,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data
            }
        )


class RolePagination(PageNumberPagination):
    """
    Custom pagination class for Role List API.
    """
    page_size = 10
    max_page_size = 100
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        total_pages = self.page.paginator.num_pages if self.page else 0
        current_page = self.page.number if self.page else 1
        page_size = self.get_page_size(self.request)
        
        return success_response(
            message="Roles retrieved successfully.",
            data={
                'count': self.page.paginator.count,
                'page': current_page,
                'page_size': page_size,
                'total_pages': total_pages,
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
                'results': data
            }
        )


