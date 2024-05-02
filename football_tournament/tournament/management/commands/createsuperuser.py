from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os
from dotenv import load_dotenv

class Command(BaseCommand):
    help = 'Create a superuser'

    def handle(self, *args, **options):
        load_dotenv()
        admin_user = os.environ['DJANGO_SUPERUSER_USERNAME']
        admin_mail = os.environ['DJANGO_SUPERUSER_EMAIL']
        adminpassword = os.environ['DJANGO_SUPERUSER_PASSWORD']

        User = get_user_model()
        if not User.objects.filter(username=admin_user).exists():
            User.objects.create_superuser(admin_user, admin_mail, adminpassword)
            self.stdout.write(self.style.SUCCESS('Successfully created new super user'))
