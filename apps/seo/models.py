from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.core.models import BaseModel

class SeoMeta(BaseModel):
    """Model for storing SEO meta information."""
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('Content Type')
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_('Object ID')
    )
    content_object = GenericForeignKey(
        'content_type',
        'object_id'
    )
    title = models.CharField(
        max_length=200,
        verbose_name=_('Title')
    )
    description = models.TextField(
        verbose_name=_('Description')
    )
    keywords = models.TextField(
        blank=True,
        verbose_name=_('Keywords')
    )
    canonical_url = models.URLField(
        blank=True,
        verbose_name=_('Canonical URL')
    )

    class Meta:
        verbose_name = _('SEO Meta')
        verbose_name_plural = _('SEO Meta')
        unique_together = ['content_type', 'object_id']

    def __str__(self):
        return f"{self.content_type} - {self.title}"

class Redirect(BaseModel):
    """Model for storing URL redirects."""
    old_path = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name=_('Old Path')
    )
    new_path = models.CharField(
        max_length=200,
        verbose_name=_('New Path')
    )
    is_permanent = models.BooleanField(
        default=True,
        verbose_name=_('Is Permanent')
    )

    class Meta:
        verbose_name = _('Redirect')
        verbose_name_plural = _('Redirects')
        unique_together = ['old_path']

    def __str__(self):
        return f"{self.old_path} -> {self.new_path}" 