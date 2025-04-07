from django.db import models
from django.contrib.auth.models import Group, Permission
from django.utils.translation import gettext_lazy as _

class Role(models.Model):
    """Role model for user roles."""
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='role'
    )
    
    class Meta:
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'
    
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        # Create or get the associated group
        if not self.pk or not self.group:
            group, created = Group.objects.get_or_create(name=self.name)
            self.group = group
        super().save(*args, **kwargs)
        # Assign permissions after save
        self.assign_permissions()

    def assign_permissions(self):
        """Assign permissions based on role type"""
        if not self.group:
            return
            
        # Clear existing permissions
        self.group.permissions.clear()
        
        if self.name == 'owner':
            # Owner has all permissions
            self.group.permissions.set(Permission.objects.all())
        elif self.name == 'manager':
            # Manager permissions
            manager_permissions = [
                'view_analytics',
                'manage_seo',
                'manage_marketing',
                'manage_support',
                'moderate_products',
            ]
            permissions = Permission.objects.filter(codename__in=manager_permissions)
            if permissions.exists():
                self.group.permissions.set(permissions)
        elif self.name == 'seller':
            # Seller permissions
            seller_permissions = [
                'view_seller_dashboard',
                'manage_own_products',
                'manage_own_categories',
                'manage_seo_fields',
                'import_export_products',
            ]
            permissions = Permission.objects.filter(codename__in=seller_permissions)
            if permissions.exists():
                self.group.permissions.set(permissions)
        elif self.name == 'user':
            # User permissions
            user_permissions = [
                'browse_products',
                'purchase_products',
                'leave_reviews',
                'track_orders',
            ]
            permissions = Permission.objects.filter(codename__in=user_permissions)
            if permissions.exists():
                self.group.permissions.set(permissions) 