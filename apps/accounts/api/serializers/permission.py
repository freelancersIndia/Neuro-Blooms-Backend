from rest_framework import serializers
from apps.accounts.models import Permission

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'code', 'group', 'description']
