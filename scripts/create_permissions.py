import os
import sys
import django

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from apps.core.models import CustomPermission

def create_permissions():
    """Create custom permissions if they don't exist."""
    
    print("Creating custom permissions...")
    
    # Get content type for CustomPermission model
    content_type, created = ContentType.objects.get_or_create(
        app_label='core',
        model='custompermission'
    )
    
    # Define custom permissions
    permissions = CustomPermission._meta.permissions
    
    # Create permissions
    for codename, name in permissions:
        permission, created = Permission.objects.get_or_create(
            codename=codename,
            name=name,
            content_type=content_type
        )
        status = 'Created' if created else 'Already exists'
        print(f"{status} permission: {name}")
    
    print("Permissions created successfully!")

if __name__ == '__main__':
    create_permissions() 