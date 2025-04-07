import os
import sys
import django

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from apps.roles.models import Role
from scripts.create_permissions import create_permissions

User = get_user_model()

# Define roles
ROLES = [
    {
        'name': 'owner',
        'description': 'Super admin with full access',
    },
    {
        'name': 'manager',
        'description': 'Manager with elevated privileges',
    },
    {
        'name': 'seller',
        'description': 'Seller with product management access',
    },
    {
        'name': 'user',
        'description': 'Regular user with basic access',
    },
]

# Define user credentials
USERS = [
    {
        'username': 'admin',
        'password': 'admin123',
        'email': 'admin@example.com',
        'is_superuser': True,
        'is_staff': True,
        'role_name': 'owner',
    },
    {
        'username': 'manager',
        'password': 'manager123',
        'email': 'manager@example.com',
        'is_staff': True,
        'role_name': 'manager',
    },
    {
        'username': 'seller',
        'password': 'seller123',
        'email': 'seller@example.com',
        'is_staff': True,
        'role_name': 'seller',
    },
    {
        'username': 'user',
        'password': 'user123',
        'email': 'user@example.com',
        'is_staff': False,
        'role_name': 'user',
    },
]

def create_roles():
    """Create roles if they don't exist."""
    print("Creating roles...")
    for role_data in ROLES:
        role, created = Role.objects.get_or_create(
            name=role_data['name'],
            defaults={'description': role_data['description']}
        )
        status = 'Created' if created else 'Already exists'
        print(f"{status} role: {role.name}")
    print("Roles created successfully!")

def create_users():
    """Create or update users with predefined credentials."""
    try:
        with transaction.atomic():
            # Create permissions first
            create_permissions()
            
            # Create roles
            create_roles()
            
            print("\nCreating users...")
            # Then create users
            for user_data in USERS:
                username = user_data.pop('username')
                password = user_data.pop('password')
                role_name = user_data.pop('role_name')
                
                # Get the role
                try:
                    role = Role.objects.get(name=role_name)
                    user_data['role'] = role
                    
                    user, created = User.objects.get_or_create(
                        username=username,
                        defaults=user_data
                    )
                    
                    # Update password regardless
                    user.set_password(password)
                    
                    # Update other fields if user already exists
                    if not created:
                        for key, value in user_data.items():
                            setattr(user, key, value)
                    
                    user.save()
                    
                    status = 'Created' if created else 'Updated'
                    print(f"{status} user: {username} with role: {role_name}")
                except Role.DoesNotExist:
                    print(f"Error: Role '{role_name}' does not exist. Skipping user '{username}'.")
            
            print("Users created successfully!")
    except Exception as e:
        print(f"Error creating users: {str(e)}")

if __name__ == '__main__':
    create_users() 