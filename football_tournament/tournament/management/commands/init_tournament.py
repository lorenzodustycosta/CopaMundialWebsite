from django.core.management.base import BaseCommand
from tournament.models import Group
import os

class Command(BaseCommand):
    help = "Inizializza i gironi"

    def handle(self, *args, **kwargs):
        num_groups = int(os.getenv('NUM_GROUPS', 4))
        existing = Group.objects.count()
        for i in range(existing + 1, num_groups + 1):
            name = "Gruppo " + chr(64 + i)  # A, B, C...
            Group.objects.create(name=name)
            self.stdout.write(f'Creato girone {name}')
