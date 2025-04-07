from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.roles.models import Role

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates default roles and users'

    def handle(self, *args, **options):
        # Create roles
        roles = {
            'owner': {
                'description': 'Full access to the platform, role management, integrations, system config',
                'users': [{'username': 'admin', 'password': 'admin123'}]
            },
            'manager': {
                'description': 'Analytics, SEO, marketing, support, product moderation',
                'users': [{'username': 'manager', 'password': 'manager123'}]
            },
            'seller': {
                'description': 'Seller dashboard, manage own products & categories, SEO fields, import/export',
                'users': [{'username': 'seller', 'password': 'seller123'}]
            },
            'user': {
                'description': 'Browse, purchase, leave reviews, track orders',
                'users': [{'username': 'user', 'password': 'user123'}]
            }
        }

        for role_name, role_data in roles.items():
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={'description': role_data['description']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created role: {role_name}'))
                role.assign_permissions()

            # Create users for this role
            for user_data in role_data['users']:
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults={
                        'role': role,
                        'is_staff': role_name in ['owner', 'manager'],
                        'is_superuser': role_name == 'owner'
                    }
                )
                if created:
                    user.set_password(user_data['password'])
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f'Created user: {user_data["username"]}'))
                else:
                    self.stdout.write(self.style.WARNING(f'User already exists: {user_data["username"]}')) 