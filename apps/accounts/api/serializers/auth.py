from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from apps.accounts.models.session import UserSession

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = [
            'id', 'ip_address', 'browser', 'device',
            'login_at', 'last_activity', 'is_active'
        ]
        read_only_fields = fields

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        # First perform standard SimpleJWT validation (checks expiry, signature etc.)
        data = super().validate(attrs)

        # Get JTI from refresh token in input
        refresh_token = RefreshToken(attrs['refresh'])
        jti = refresh_token.payload.get('jti')

        # Check if corresponding UserSession exists and is active
        try:
            session = UserSession.objects.get(refresh_token_jti=jti, is_active=True)
        except UserSession.DoesNotExist:
            raise InvalidToken("This session is no longer active or invalid.")

        now = timezone.now()
        # If SimpleJWT rotated the refresh token, update JTI in session
        if 'refresh' in data:
            new_refresh = RefreshToken(data['refresh'])
            new_jti = new_refresh.payload.get('jti')
            session.refresh_token_jti = new_jti
            session.save()

        # Update last activity timestamp
        session.last_activity = now
        session.save(update_fields=['last_activity', 'refresh_token_jti'] if 'refresh' in data else ['last_activity'])

        return data
