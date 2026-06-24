from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Seed legado: delega para importar_planilha_atual.'

    def handle(self, *args, **options):
        call_command('importar_planilha_atual')
