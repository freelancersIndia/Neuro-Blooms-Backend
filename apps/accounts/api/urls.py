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
    RoleViewSet,
)
from apps.accounts.api.views.doctor import DoctorListView, DoctorDetailView

router = DefaultRouter()
# Route GET /api/v1/users/, POST /api/v1/users/, etc.
router.register('users', UserAdminViewSet, basename='users')
# Route GET /api/v1/sessions/, DELETE /api/v1/sessions/{id}/, POST /api/v1/sessions/logout-all/
router.register('sessions', UserSessionViewSet, basename='sessions')
# Route GET /api/v1/roles/, POST /api/v1/roles/, etc.
router.register('roles', RoleViewSet, basename='roles')

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

    # Doctor directory endpoints
    path('doctors/', DoctorListView.as_view(), name='doctor_list'),
    path('doctors/<uuid:id>/', DoctorDetailView.as_view(), name='doctor_detail'),

    # Security Log endpoints (Admin only)
    path('security-logs/', SecurityLogListView.as_view(), name='security_logs'),

    # Router registered views (Users and Sessions)
    path('users/<uuid:id>/sessions/<uuid:session_id>/revoke/', UserAdminViewSet.as_view({'post': 'session_revoke'}), name='user_session_revoke'),
    path('', include(router.urls)),
]
