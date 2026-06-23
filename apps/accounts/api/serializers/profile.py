from rest_framework import serializers
from apps.accounts.models.user import User

class ProfileSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'profile_image', 'is_verified', 'roles', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'email', 'is_verified', 'roles', 'created_at', 'updated_at']

    def get_roles(self, obj) -> list:
        return [role.name for role in obj.roles.all()]
