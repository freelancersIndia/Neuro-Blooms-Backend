from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.accounts.models.user import User, Role, UserRole, FailedLoginAttempt, AccountLock
from apps.accounts.models.otp import OTP
from apps.accounts.models.session import UserSession
from apps.accounts.models.activity_log import ActivityLog

class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'phone_number', 'is_active', 'is_verified', 'created_at')
    list_filter = ('is_active', 'is_verified', 'created_at')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number', 'profile_image')}),
        ('Permissions', {'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('last_login', 'created_at', 'updated_at')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')

class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'assigned_at')
    list_filter = ('role', 'assigned_at')
    search_fields = ('user__email', 'role__name')

class OTPAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_code', 'purpose', 'expires_at', 'is_used', 'created_at')
    list_filter = ('purpose', 'is_used', 'created_at')
    search_fields = ('user__email', 'otp_code')

class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'device', 'browser', 'ip_address', 'login_at', 'last_activity', 'is_active')
    list_filter = ('is_active', 'login_at', 'last_activity')
    search_fields = ('user__email', 'device', 'browser', 'ip_address')

class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'description', 'ip_address', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('user__email', 'description', 'ip_address')

class FailedLoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('email', 'ip_address', 'reason', 'attempt_time')
    list_filter = ('reason', 'attempt_time')
    search_fields = ('email', 'ip_address')

class AccountLockAdmin(admin.ModelAdmin):
    list_display = ('user', 'locked_at', 'unlock_at', 'reason', 'is_active')
    list_filter = ('is_active', 'locked_at', 'unlock_at')
    search_fields = ('user__email', 'reason')

# Register models in admin panel
admin.site.register(User, UserAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(UserRole, UserRoleAdmin)
admin.site.register(OTP, OTPAdmin)
admin.site.register(UserSession, UserSessionAdmin)
admin.site.register(ActivityLog, ActivityLogAdmin)
admin.site.register(FailedLoginAttempt, FailedLoginAttemptAdmin)
admin.site.register(AccountLock, AccountLockAdmin)
