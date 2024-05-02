from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = 'Check if a superuser exists'

    def handle(self, *args, **options):
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("A superuser exists.")
            exit(0)  # Exits successfully, indicating superuser exists
        else:
            self.stdout.write("No superuser found.")
            exit(1)  # Exits with error, indicating no superuser exists
