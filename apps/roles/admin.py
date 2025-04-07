from django.contrib import admin
from .models import Role

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name', 'description']
    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
    ) 