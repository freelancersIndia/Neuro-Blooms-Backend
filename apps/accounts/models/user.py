import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)

        user = self.create_user(email, password, **extra_fields)

        # Assign ADMIN role to superuser automatically
        admin_role, _ = Role.objects.get_or_create(name='ADMIN')
        UserRole.objects.get_or_create(user=user, role=admin_role)

        return user

class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', null=True, blank=True)
    specialization = models.CharField(max_length=255, blank=True, null=True, verbose_name="Specialization")
    qualification = models.CharField(max_length=255, blank=True, null=True, verbose_name="Qualification")
    experience = models.PositiveIntegerField(default=0, verbose_name="Experience (Years)")
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    roles = models.ManyToManyField(Role, through='UserRole', related_name='users')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    def has_role(self, role_name: str) -> bool:
        return self.user_roles.filter(role__name=role_name).exists()

    def has_any_role(self, list_of_roles: list) -> bool:
        return self.user_roles.filter(role__name__in=list_of_roles).exists()

class UserRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='user_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user.email} - {self.role.name}"

class FailedLoginAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    attempt_time = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.email} from {self.ip_address} failed at {self.attempt_time} (Reason: {self.reason})"

class AccountLock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='locks')
    locked_at = models.DateTimeField(auto_now_add=True)
    unlock_at = models.DateTimeField()
    reason = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        status = "Active" if self.is_active and self.unlock_at > timezone.now() else "Expired"
        return f"{self.user.email} locked until {self.unlock_at} ({status})"
