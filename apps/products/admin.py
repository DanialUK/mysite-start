from django.contrib import admin
from .models import Category, Product, Attribute, AttributeValue, ProductImage, ProductAttribute, Review

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

class ProductAttributeInline(admin.TabularInline):
    model = ProductAttribute
    extra = 1

class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ['user', 'rating', 'comment', 'created_at']
    can_delete = False
    max_num = 0
    show_change_link = True

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'is_active']
    search_fields = ['name', 'description']
    list_filter = ['is_active', 'parent']
    prepopulated_fields = {'slug': ('name',)}
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'description', 'image', 'is_active')
        }),
    )

@admin.register(Attribute)
class AttributeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(AttributeValue)
class AttributeValueAdmin(admin.ModelAdmin):
    list_display = ['attribute', 'value']
    search_fields = ['value']
    list_filter = ['attribute']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'stock', 'is_active', 'featured']
    search_fields = ['name', 'description', 'sku']
    list_filter = ['is_active', 'featured', 'category', 'created_at']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductAttributeInline, ReviewInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Pricing & Inventory', {
            'fields': ('price', 'stock', 'sku')
        }),
        ('Options', {
            'fields': ('is_active', 'featured')
        }),
    )
    
    def get_reviews_count(self, obj):
        return obj.get_review_count()
    get_reviews_count.short_description = 'Reviews'
    
    def get_avg_rating(self, obj):
        return obj.get_average_rating()
    get_avg_rating.short_description = 'Rating'

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'alt_text', 'is_featured']
    list_filter = ['is_featured', 'product']
    search_fields = ['product__name', 'alt_text']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_approved', 'created_at']
    search_fields = ['product__name', 'user__username', 'comment']
    readonly_fields = ['created_at']
    actions = ['approve_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = 'Approve selected reviews' 