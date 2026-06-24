from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, AuthenticationFailed, NotAuthenticated
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework import status
from rest_framework.response import Response
from apps.accounts.utils.responses import error_response

def custom_exception_handler(exc, context):
    """
    Custom exception handler to standardize DRF error responses.
    """
    # Call DRF's default exception handler first to get the standard error response
    response = exception_handler(exc, context)

    # If response is None, it means it's not a DRF exception (e.g. standard Django or Python exception)
    if response is None:
        return None

    # Handle Validation Errors
    if isinstance(exc, ValidationError):
        return error_response(
            message="Validation failed.",
            errors=response.data,
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # Handle SimpleJWT's InvalidToken or other Authentication errors
    if isinstance(exc, (InvalidToken, AuthenticationFailed, NotAuthenticated)):
        message = "Invalid credentials."
        # Task 1 requires an exact return structure when a session is expired or revoked
        if isinstance(exc, InvalidToken) and str(exc) == "Session expired or revoked.":
            return Response({
                "success": False,
                "message": "Session expired or revoked."
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        if hasattr(exc, 'detail'):
            if isinstance(exc.detail, dict) and 'detail' in exc.detail:
                message = str(exc.detail['detail'])
            elif isinstance(exc.detail, str):
                message = exc.detail
            elif hasattr(exc.detail, 'detail'):
                message = str(exc.detail.detail)
            else:
                message = str(exc.detail)
            
        return error_response(
            message=message,
            errors=None,
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    # Handle other DRF exceptions (PermissionDenied, NotFound, MethodNotAllowed, etc.)
    message = "An error occurred."
    if hasattr(exc, 'detail'):
        if isinstance(exc.detail, dict) and 'detail' in exc.detail:
            message = str(exc.detail['detail'])
        elif isinstance(exc.detail, str):
            message = exc.detail
        elif hasattr(exc.detail, 'detail'):
            message = str(exc.detail.detail)
        else:
            message = str(exc.detail)

    return error_response(
        message=message,
        errors=None,
        status_code=response.status_code
    )
