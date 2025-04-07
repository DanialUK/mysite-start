from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

class BaseModel(models.Model):
    """Base model with common fields for all models."""
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )

    class Meta:
        abstract = True

class Setting(BaseModel):
    """Model for storing application settings."""
    key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('Key')
    )
    value = models.TextField(
        verbose_name=_('Value')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )

    class Meta:
        verbose_name = _('Setting')
        verbose_name_plural = _('Settings')
        ordering = ['key']

    def __str__(self):
        return self.key

# Create a ContentType for custom permissions
class CustomPermission(models.Model):
    """Custom permissions model."""
    
    class Meta:
        managed = False  # No database table creation
        default_permissions = ()  # disable default permissions
        permissions = (
            # Manager permissions
            ('view_analytics', 'Can view analytics'),
            ('manage_seo', 'Can manage SEO'),
            ('manage_marketing', 'Can manage marketing'),
            ('manage_support', 'Can manage support'),
            ('moderate_products', 'Can moderate products'),
            
            # Seller permissions
            ('view_seller_dashboard', 'Can view seller dashboard'),
            ('manage_own_products', 'Can manage own products'),
            ('manage_own_categories', 'Can manage own categories'),
            ('manage_seo_fields', 'Can manage SEO fields'),
            ('import_export_products', 'Can import/export products'),
            
            # User permissions
            ('browse_products', 'Can browse products'),
            ('purchase_products', 'Can purchase products'),
            ('leave_reviews', 'Can leave reviews'),
            ('track_orders', 'Can track orders'),
        ) 