import re
import unicodedata

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from escalas.models import UsuarioEscala


DEFAULT_PASSWORD = 'Escala@2026'


def gerar_username(nome):
    normalizado = unicodedata.normalize('NFKD', nome)
    sem_acentos = ''.join(ch for ch in normalizado if not unicodedata.combining(ch))
    username = re.sub(r'[^a-z0-9]+', '.', sem_acentos.lower()).strip('.')
    return re.sub(r'\.+', '.', username)


class Command(BaseCommand):
    help = 'Cria e vincula usuarios Django padrao para os gerentes ativos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            default=DEFAULT_PASSWORD,
            help='Senha inicial para usuarios criados. Padrao: Escala@2026.',
        )
        parser.add_argument(
            '--reset-password',
            action='store_true',
            help='Tambem redefine a senha dos usuarios existentes vinculados aos gerentes.',
        )

    def handle(self, *args, **options):
        password = options['password']
        reset_password = options['reset_password']
        User = get_user_model()

        criados = 0
        atualizados = 0

        for gerente in UsuarioEscala.objects.filter(ativo=True).order_by('nome'):
            username = gerar_username(gerente.nome)
            user = gerente.user or User.objects.filter(username=username).first()

            if user is None:
                user = User.objects.create_user(username=username, password=password)
                criados += 1
                status = 'CRIADO'
            else:
                if reset_password and not user.is_superuser:
                    user.set_password(password)
                atualizados += 1
                status = 'OK'

            if not user.is_superuser:
                partes = gerente.nome.title().split()
                user.first_name = partes[0] if partes else ''
                user.last_name = ' '.join(partes[1:]) if len(partes) > 1 else ''
                user.is_staff = False
                user.is_superuser = False
            user.is_active = True
            user.save()

            if gerente.user_id != user.id:
                gerente.user = user
                gerente.save(update_fields=['user'])

            self.stdout.write(
                f'  [{status}] {gerente.nome} -> {user.username} '
                f'({"administrador" if user.is_superuser else "usuario padrao"})'
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'[OK] Usuarios padrao sincronizados. Criados: {criados}. Existentes: {atualizados}.'
            )
        )
