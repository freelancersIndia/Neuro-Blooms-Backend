from rest_framework import serializers
from apps.accounts.models.user import User

class ProfileSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'profile_image', 'is_verified', 'roles', 'created_at', 'updated_at',
            'specialization', 'qualification', 'experience', 'last_login', 'is_active'
        ]
        read_only_fields = ['id', 'email', 'is_verified', 'roles', 'created_at', 'updated_at', 'last_login', 'is_active']

    def get_roles(self, obj) -> list:
        return [role.name for role in obj.roles.all()]

    def get_profile_image(self, obj) -> str:
        if not obj.profile_image:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url
