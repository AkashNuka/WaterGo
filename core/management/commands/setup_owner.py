from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction
from django.db.utils import ProgrammingError
from core.models import User

class Command(BaseCommand):
    help = 'Creates the default owner account with hardcoded credentials'

    def handle(self, *args, **kwargs):
        try:
            # Run migrations first
            self.stdout.write('Running migrations...')
            call_command('migrate')
            
            owner_username = 'owner'
            owner_email = 'owner@watergo.com'
            owner_password = 'waterowner123'  # In production, use a more secure password
            
            with transaction.atomic():
                # Check if owner already exists
                if User.objects.filter(username=owner_username).exists():
                    self.stdout.write(self.style.WARNING(f'Owner account "{owner_username}" already exists'))
                    return
                
                # Create owner account
                owner = User.objects.create_user(
                    username=owner_username,
                    email=owner_email,
                    password=owner_password,
                    role='OWNER',
                    is_staff=True  # Give admin site access but not superuser
                )
                
                self.stdout.write(self.style.SUCCESS(f'Successfully created owner account: {owner_username}'))
                self.stdout.write(self.style.SUCCESS(f'Email: {owner_email}'))
                self.stdout.write(self.style.SUCCESS(f'Password: {owner_password}'))
                
        except ProgrammingError as e:
            self.stdout.write(self.style.ERROR('Database error occurred. Make sure your database is properly configured.'))
            raise e