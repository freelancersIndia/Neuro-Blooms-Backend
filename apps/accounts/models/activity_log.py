import uuid
from django.db import models
from apps.accounts.models.user import User
from apps.accounts.constants.activity_types import ActivityType

class ActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_logs')
    target_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='target_activity_logs')
    action = models.CharField(max_length=50, choices=ActivityType.CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_email = self.user.email if self.user else "Anonymous"
        return f"{user_email} - {self.action} at {self.created_at}"
