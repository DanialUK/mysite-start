from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from roles.models import Role

class Command(BaseCommand):
    help = 'Creates default users for testing'

    def handle(self, *args, **kwargs):
        # List of default users with their roles
        default_users = [
            {
                'username': 'admin',
                'password': 'admin123',
                'is_staff': True,
                'is_superuser': True,
                'role': 'owner'
            },
            {
                'username': 'manager',
                'password': 'manager123',
                'role': 'manager'
            },
            {
                'username': 'seller',
                'password': 'seller123',
                'role': 'seller'
            },
            {
                'username': 'user',
                'password': 'user123',
                'role': 'user'
            }
        ]

        for user_data in default_users:
            username = user_data['username']
            if not User.objects.filter(username=username).exists():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    password=user_data['password'],
                    is_staff=user_data.get('is_staff', False),
                    is_superuser=user_data.get('is_superuser', False)
                )
                
                # Set _skip_role_creation to True to prevent signal from creating default role
                user._skip_role_creation = True
                user.save()
                
                # Create role manually
                Role.objects.create(
                    user=user,
                    role_type=user_data['role']
                )
                
                self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}"'))
            else:
                self.stdout.write(self.style.WARNING(f'User "{username}" already exists')) 