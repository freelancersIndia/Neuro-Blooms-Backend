from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.accounts.api.views import (
    LoginView,
    LogoutView,
    CustomTokenRefreshView,
    SendOTPView,
    VerifyOTPView,
    ForgotPasswordView,
    ResetPasswordView,
    ChangePasswordView,
    ResendVerificationView,
    ProfileView,
    UserSessionViewSet,
    UserAdminViewSet,
    SecurityLogListView,
)

router = DefaultRouter()
# Route GET /api/v1/users/, POST /api/v1/users/, etc.
router.register('users', UserAdminViewSet, basename='users')
# Route GET /api/v1/sessions/, DELETE /api/v1/sessions/{id}/, POST /api/v1/sessions/logout-all/
router.register('sessions', UserSessionViewSet, basename='sessions')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', LoginView.as_view(), name='auth_login'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='auth_resend_verification'),

    # OTP endpoints
    path('auth/send-otp/', SendOTPView.as_view(), name='auth_send_otp'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='auth_verify_otp'),

    # Password management endpoints
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='auth_forgot_password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='auth_reset_password'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth_change_password'),

    # Profile endpoints
    path('profile/me/', ProfileView.as_view(), name='profile_me'),

    # Security Log endpoints (Admin only)
    path('security-logs/', SecurityLogListView.as_view(), name='security_logs'),

    # Router registered views (Users and Sessions)
    path('', include(router.urls)),
]
