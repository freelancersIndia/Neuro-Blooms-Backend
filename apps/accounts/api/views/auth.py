from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.utils.ip import get_client_ip
from apps.accounts.services.auth_service import AuthService
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.session_service import SessionService
from apps.accounts.models.user import User
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.otp_types import OTPPurpose
from apps.accounts.constants.activity_types import ActivityType

from apps.accounts.api.serializers.auth import LoginSerializer, CustomTokenRefreshSerializer
from apps.accounts.api.serializers.otp import SendOTPSerializer, VerifyOTPSerializer
from apps.accounts.api.serializers.password import (
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        ip_address = get_client_ip(request)

        try:
            AuthService.validate_credentials_and_send_otp(
                email=email,
                password=password,
                ip_address=ip_address
            )
            return Response({
                'detail': 'Credentials verified. A login verification OTP has been sent to your email.'
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [AllowAny]  # Let refresh token validation be handled in the service

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'detail': 'Refresh token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        ip_address = get_client_ip(request)
        try:
            AuthService.logout_user(refresh_token, ip_address)
            return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer

class SendOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        purpose = serializer.validated_data['purpose']
        ip_address = get_client_ip(request)

        try:
            user = User.objects.get(email=email)
            OTPService.generate_otp(user, purpose, ip_address)
        except User.DoesNotExist:
            # Silently accept to prevent email enumeration
            pass

        return Response({'detail': 'If the email exists, an OTP has been sent.'}, status=status.HTTP_200_OK)

class VerifyOTPView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        otp_code = serializer.validated_data['otp_code']
        purpose = serializer.validated_data['purpose']
        ip_address = get_client_ip(request)

        try:
            # If purpose is LOGIN_VERIFICATION, verify and return tokens + user data + roles
            if purpose == OTPPurpose.LOGIN_VERIFICATION:
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                auth_data = AuthService.verify_login_otp(
                    email=email,
                    otp_code=otp_code,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                return Response({
                    'access': auth_data['access'],
                    'refresh': auth_data['refresh'],
                    'user': {
                        'email': auth_data['user'].email,
                        'first_name': auth_data['user'].first_name,
                        'last_name': auth_data['user'].last_name,
                        'roles': [role.name for role in auth_data['user'].roles.all()]
                    }
                }, status=status.HTTP_200_OK)

            token = OTPService.verify_otp(email, otp_code, purpose, ip_address)

            # If purpose is EMAIL_VERIFICATION, mark user as verified immediately
            if purpose == OTPPurpose.EMAIL_VERIFICATION:
                user = User.objects.get(email=email)
                user.is_verified = True
                user.save()

                ActivityLog.objects.create(
                    user=user,
                    action=ActivityType.USER_UPDATED,
                    description="User email verified via OTP.",
                    ip_address=ip_address
                )

            return Response({
                'detail': 'OTP verified successfully.',
                'token': token
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        ip_address = get_client_ip(request)

        AuthService.forgot_password(email, ip_address)
        return Response({'detail': 'If the email exists, a password reset OTP has been sent.'}, status=status.HTTP_200_OK)

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        ip_address = get_client_ip(request)

        try:
            AuthService.reset_password(token, new_password, ip_address)
            return Response({'detail': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        current_password = serializer.validated_data['current_password']
        new_password = serializer.validated_data['new_password']
        ip_address = get_client_ip(request)

        try:
            AuthService.change_password(request.user, current_password, new_password, ip_address)
            return Response({'detail': 'Password has been changed successfully.'}, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
