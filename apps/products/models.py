from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel
from django.utils.text import slugify

class Category(BaseModel):
    """Model for product categories."""
    name = models.CharField(
        max_length=100,
        verbose_name=_('Name')
    )
    slug = models.SlugField(
        unique=True,
        verbose_name=_('Slug')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Parent Category')
    )
    image = models.ImageField(
        upload_to='categories',
        blank=True,
        null=True,
        verbose_name=_('Image')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )

    class Meta:
        verbose_name = _('Category')
        verbose_name_plural = _('Categories')
        ordering = ['name']

    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('products:category_detail', args=[self.slug])

class Attribute(BaseModel):
    """Model for product attributes."""
    name = models.CharField(
        max_length=100,
        verbose_name=_('Name')
    )
    slug = models.SlugField(
        unique=True,
        verbose_name=_('Slug')
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Description')
    )
    
    class Meta:
        verbose_name = _('Attribute')
        verbose_name_plural = _('Attributes')
        ordering = ['name']
    
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class AttributeValue(BaseModel):
    """Model for attribute values."""
    attribute = models.ForeignKey(
        Attribute,
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name=_('Attribute')
    )
    value = models.CharField(
        max_length=100,
        verbose_name=_('Value')
    )
    
    class Meta:
        verbose_name = _('Attribute Value')
        verbose_name_plural = _('Attribute Values')
        unique_together = ('attribute', 'value')
        ordering = ['attribute', 'value']
    
    def __str__(self):
        return f"{self.attribute}: {self.value}"

class Product(BaseModel):
    """Model for products."""
    name = models.CharField(
        max_length=200,
        verbose_name=_('Name')
    )
    slug = models.SlugField(
        unique=True,
        verbose_name=_('Slug')
    )
    description = models.TextField(
        verbose_name=_('Description')
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_('Price')
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name=_('Category')
    )
    stock = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Stock')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    attributes = models.ManyToManyField(
        AttributeValue,
        through='ProductAttribute',
        related_name='products',
        verbose_name=_('Attributes')
    )
    featured = models.BooleanField(
        default=False,
        verbose_name=_('Featured')
    )
    sku = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('SKU')
    )

    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['-created_at']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        
    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('products:product_detail', args=[self.slug])
        
    def get_average_rating(self):
        reviews = self.reviews.all()
        if reviews:
            avg = reviews.aggregate(models.Avg('rating'))['rating__avg']
            return round(avg, 1)
        return 0
        
    def get_review_count(self):
        return self.reviews.count()

class ProductImage(BaseModel):
    """Model for product images."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Product')
    )
    image = models.ImageField(
        upload_to='products',
        verbose_name=_('Image')
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        verbose_name=_('Alternative Text')
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name=_('Is Featured')
    )
    
    class Meta:
        verbose_name = _('Product Image')
        verbose_name_plural = _('Product Images')
        ordering = ['-is_featured', 'id']
    
    def __str__(self):
        return f"Image for {self.product.name}"

class ProductAttribute(BaseModel):
    """Model for product attributes."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='product_attributes',
        verbose_name=_('Product')
    )
    attribute_value = models.ForeignKey(
        AttributeValue,
        on_delete=models.CASCADE,
        related_name='product_attributes',
        verbose_name=_('Attribute Value')
    )
    
    class Meta:
        verbose_name = _('Product Attribute')
        verbose_name_plural = _('Product Attributes')
        unique_together = ('product', 'attribute_value')
    
    def __str__(self):
        return f"{self.product.name} - {self.attribute_value}"

class Review(BaseModel):
    """Model for product reviews."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('Product')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('User')
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Rating')
    )
    comment = models.TextField(
        verbose_name=_('Comment')
    )
    is_approved = models.BooleanField(
        default=False,
        verbose_name=_('Is Approved')
    )
    
    class Meta:
        verbose_name = _('Review')
        verbose_name_plural = _('Reviews')
        unique_together = ('product', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Review by {self.user.username} for {self.product.name}" 