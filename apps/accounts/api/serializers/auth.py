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
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            'id', 'ip_address', 'browser', 'device', 'location',
            'login_at', 'last_activity', 'is_active', 'is_current'
        ]
        read_only_fields = fields

    def get_is_current(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.auth:
            return False
        # Retrieve session_jti from the access token payload
        session_jti = request.auth.get('session_jti')
        return obj.refresh_token_jti == session_jti

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            # First perform standard SimpleJWT validation (checks expiry, signature, blacklist etc.)
            data = super().validate(attrs)
        except Exception:
            raise InvalidToken("Session expired or revoked.")

        # Get JTI from refresh token in input
        try:
            refresh_token = RefreshToken(attrs['refresh'])
            jti = refresh_token.payload.get('jti')
        except Exception:
            raise InvalidToken("Session expired or revoked.")

        # Check if corresponding UserSession exists and is active
        try:
            session = UserSession.objects.get(refresh_token_jti=jti, is_active=True)
        except UserSession.DoesNotExist:
            raise InvalidToken("Session expired or revoked.")

        now = timezone.now()
        # If SimpleJWT rotated the refresh token, update JTI in session
        if 'refresh' in data:
            new_refresh = RefreshToken(data['refresh'])
            new_jti = new_refresh.payload.get('jti')
            session.refresh_token_jti = new_jti
            session.save()
            # Inject new session JTI into the rotated access token
            new_refresh.access_token['session_jti'] = new_jti
            data['access'] = str(new_refresh.access_token)
        else:
            # If refresh token was not rotated, inject the current JTI into the new access token
            refresh_token.access_token['session_jti'] = jti
            data['access'] = str(refresh_token.access_token)

        # Update last activity timestamp
        session.last_activity = now
        session.save(update_fields=['last_activity', 'refresh_token_jti'] if 'refresh' in data else ['last_activity'])

        return data
