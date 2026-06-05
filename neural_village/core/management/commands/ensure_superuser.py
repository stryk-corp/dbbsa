import os
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Ensure a deploy superuser exists using env vars or default credentials.'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('DEPLOY_SUPERUSER_USERNAME', 'admin')
        password = os.environ.get('DEPLOY_SUPERUSER_PASSWORD', 'admin123')
        email = os.environ.get('DEPLOY_SUPERUSER_EMAIL', 'admin@dbbsa.com')

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(f'Superuser "{username}" already exists.'))
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Created superuser "{username}".'))
