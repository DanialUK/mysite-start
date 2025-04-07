from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.roles.models import Role

class User(AbstractUser):
    """Custom user model."""
    
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('Role')
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_('Phone Number')
    )
    address = models.TextField(
        blank=True,
        verbose_name=_('Address')
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_('Is Verified')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.username} ({self.get_full_name()})"

    def save(self, *args, **kwargs):
        if not self.pk and not self.role:
            # Set default role for new users
            try:
                default_role = Role.objects.get(name='user')
            except Role.DoesNotExist:
                default_role = Role.objects.create(name='user', description='Regular user with basic access')
            self.role = default_role
        super().save(*args, **kwargs)

    # Add custom fields here if needed 