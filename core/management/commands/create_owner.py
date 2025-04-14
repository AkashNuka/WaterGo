from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a default owner account for testing'

    def handle(self, *args, **kwargs):
        username = 'owner'
        email = 'owner@watergo.com'
        password = 'ownerpass123'

        with transaction.atomic():
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f'Owner user "{username}" already exists.'))
                return
                
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role='OWNER'
            )
            
            self.stdout.write(self.style.SUCCESS(f'''
            Successfully created owner account:
            Username: {username}
            Email: {email}
            Password: {password}
            
            Use these credentials to log in as an owner.
            '''))