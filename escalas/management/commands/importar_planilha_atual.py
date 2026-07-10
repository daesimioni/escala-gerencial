from collections import Counter, defaultdict
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from escalas.models import (
    BloqueioUsuario, ConfiguracaoSistema, EscalaBloco, EscalaDia, Feriado,
    GrupoEscala, HistoricoAlteracao, MesFechado, UsuarioEscala,
)
from escalas.services import (
    DATA_CORTE_HISTORICO, FERIADOS_ESTADUAIS_PR, FERIADOS_MUNICIPAIS_CURITIBA,
    FERIADOS_NACIONAIS_FIXOS, HISTORICO_FIM, HISTORICO_INICIO,
    MOTIVO_BUFFER_FERIAS, _atualizar_contadores_usuarios,
    get_blocos_cobertura, get_feriados_moveis, regenerar_apos_data,
    sincronizar_buffers_ferias_usuario,
)


IMPORTACAO_HISTORICO_FIM = date(2026, 7, 9)
GERACAO_FUTURA_INICIO = date(2026, 7, 10)

USUARIOS_CIDIS_2026 = [
    ('SAMUEL BITELO', 'DOTR', '41 99826-2343', 'A'),
    ('HENRY WILLIAM', 'VOTRV', '41 99556-1071', 'A'),
    ('JEZIEL', 'VOTRM', '41 99131-3791', 'A'),
    ('PANGARTTE', 'VOPCP', '41 99239-5912', 'A'),
    ('JULIANO MOSKO', 'VOQTR', '42 99155-4541', 'A'),
    ('MARCOS VINICIUS', 'VIPOP', '41 99169-4582', 'B'),
    ('RONALDO JR', 'VAPOP', '41 99694-5975', 'B'),
    ('LUIZ ROBERTO', 'DDCQ', '43 99191-2359', 'B'),
    ('DIONIZIO', 'VDSED', '41 98884-7269', 'B'),
]

EX_GERENTES_CIDIS_2026 = [
    'GUSTAVO THEODOR',
    'JEFFERSON FRANCO',
    'MARCELO',
]

FERIAS_CIDIS_2026 = [
    ('SAMUEL BITELO', '2026-08-17', '2026-08-31'),
    ('HENRY WILLIAM', '2026-01-12', '2026-01-16'),
    ('JEZIEL', '2026-01-01', '2026-01-11'),
    ('JEZIEL', '2026-06-08', '2026-06-12'),
    ('JEZIEL', '2026-07-20', '2026-07-29'),
    ('PANGARTTE', '2026-01-19', '2026-01-30'),
    ('PANGARTTE', '2026-07-13', '2026-07-17'),
    ('JULIANO MOSKO', '2026-02-02', '2026-02-12'),
    ('JULIANO MOSKO', '2026-05-04', '2026-05-08'),
    ('JULIANO MOSKO', '2026-08-24', '2026-09-06'),
    ('MARCOS VINICIUS', '2026-01-26', '2026-01-30'),
    ('MARCOS VINICIUS', '2026-04-22', '2026-05-05'),
    ('MARCOS VINICIUS', '2026-10-13', '2026-10-23'),
    ('MARCOS VINICIUS', '2026-12-07', '2026-12-11'),
    ('RONALDO JR', '2026-04-06', '2026-04-12'),
    ('RONALDO JR', '2026-07-13', '2026-07-24'),
    ('RONALDO JR', '2027-01-04', '2027-01-21'),
    ('LUIZ ROBERTO', '2026-04-17', '2026-04-17'),
    ('LUIZ ROBERTO', '2026-04-20', '2026-04-20'),
    ('LUIZ ROBERTO', '2026-06-16', '2026-07-03'),
    ('LUIZ ROBERTO', '2026-08-24', '2026-09-04'),
    ('DIONIZIO', '2026-02-18', '2026-02-28'),
    ('DIONIZIO', '2026-06-01', '2026-06-14'),
]

MARCACOES_TRABALHO_CIDIS_2026 = [
    ('2026-01-03', 'SAMUEL BITELO', 'S1'),
    ('2026-01-04', 'SAMUEL BITELO', 'S2'),
    ('2026-01-31', 'SAMUEL BITELO', 'S1'),
    ('2026-02-01', 'SAMUEL BITELO', 'S2'),
    ('2026-02-28', 'SAMUEL BITELO', 'S1'),
    ('2026-03-01', 'SAMUEL BITELO', 'S2'),
    ('2026-04-03', 'SAMUEL BITELO', 'S1'),
    ('2026-04-04', 'SAMUEL BITELO', 'S1'),
    ('2026-04-05', 'SAMUEL BITELO', 'S2'),
    ('2026-04-26', 'SAMUEL BITELO', 'S1'),
    ('2026-05-09', 'SAMUEL BITELO', 'S2'),
    ('2026-05-10', 'SAMUEL BITELO', 'S1'),
    ('2026-06-04', 'SAMUEL BITELO', 'S1'),
    ('2026-06-06', 'SAMUEL BITELO', 'S1'),
    ('2026-06-07', 'SAMUEL BITELO', 'S1'),
    ('2026-06-28', 'SAMUEL BITELO', 'S1'),
    ('2026-01-24', 'HENRY WILLIAM', 'S2'),
    ('2026-01-25', 'HENRY WILLIAM', 'S1'),
    ('2026-04-11', 'HENRY WILLIAM', 'S1'),
    ('2026-04-12', 'HENRY WILLIAM', 'S2'),
    ('2026-05-01', 'HENRY WILLIAM', 'S1'),
    ('2026-05-02', 'HENRY WILLIAM', 'S1'),
    ('2026-05-03', 'HENRY WILLIAM', 'S2'),
    ('2026-05-30', 'HENRY WILLIAM', 'S2'),
    ('2026-05-31', 'HENRY WILLIAM', 'S1'),
    ('2026-01-17', 'JEZIEL', 'S1'),
    ('2026-01-18', 'JEZIEL', 'S2'),
    ('2026-02-07', 'JEZIEL', 'S1'),
    ('2026-02-08', 'JEZIEL', 'S2'),
    ('2026-02-28', 'JEZIEL', 'S2'),
    ('2026-03-01', 'JEZIEL', 'S1'),
    ('2026-03-28', 'JEZIEL', 'S2'),
    ('2026-03-29', 'JEZIEL', 'S1'),
    ('2026-04-21', 'JEZIEL', 'S1'),
    ('2026-04-25', 'JEZIEL', 'S1'),
    ('2026-04-26', 'JEZIEL', 'S2'),
    ('2026-05-16', 'JEZIEL', 'S1'),
    ('2026-05-17', 'JEZIEL', 'S2'),
    ('2026-06-27', 'JEZIEL', 'S1'),
    ('2026-02-14', 'PANGARTTE', 'S1'),
    ('2026-02-15', 'PANGARTTE', 'S2'),
    ('2026-02-17', 'PANGARTTE', 'S1'),
    ('2026-03-14', 'PANGARTTE', 'S1'),
    ('2026-03-15', 'PANGARTTE', 'S2'),
    ('2026-04-21', 'PANGARTTE', 'S2'),
    ('2026-04-25', 'PANGARTTE', 'S2'),
    ('2026-05-09', 'PANGARTTE', 'S1'),
    ('2026-05-10', 'PANGARTTE', 'S2'),
    ('2026-06-14', 'PANGARTTE', 'S1'),
    ('2026-01-24', 'JULIANO MOSKO', 'S1'),
    ('2026-01-25', 'JULIANO MOSKO', 'S2'),
    ('2026-03-21', 'JULIANO MOSKO', 'S1'),
    ('2026-03-22', 'JULIANO MOSKO', 'S2'),
    ('2026-04-18', 'JULIANO MOSKO', 'S1'),
    ('2026-04-19', 'JULIANO MOSKO', 'S1'),
    ('2026-05-30', 'JULIANO MOSKO', 'S1'),
    ('2026-05-31', 'JULIANO MOSKO', 'S2'),
    ('2026-06-20', 'JULIANO MOSKO', 'S1'),
    ('2026-02-21', 'MARCOS VINICIUS', 'S2'),
    ('2026-02-22', 'MARCOS VINICIUS', 'S1'),
    ('2026-03-28', 'MARCOS VINICIUS', 'S1'),
    ('2026-03-29', 'MARCOS VINICIUS', 'S2'),
    ('2026-05-16', 'MARCOS VINICIUS', 'S2'),
    ('2026-05-17', 'MARCOS VINICIUS', 'S1'),
    ('2026-07-04', 'MARCOS VINICIUS', 'S1'),
    ('2026-01-31', 'RONALDO JR', 'S2'),
    ('2026-02-01', 'RONALDO JR', 'S1'),
    ('2026-02-14', 'RONALDO JR', 'S2'),
    ('2026-02-15', 'RONALDO JR', 'S1'),
    ('2026-02-17', 'RONALDO JR', 'S2'),
    ('2026-03-14', 'RONALDO JR', 'S2'),
    ('2026-03-15', 'RONALDO JR', 'S1'),
    ('2026-04-18', 'RONALDO JR', 'S2'),
    ('2026-04-19', 'RONALDO JR', 'S2'),
    ('2026-05-23', 'RONALDO JR', 'S2'),
    ('2026-05-24', 'RONALDO JR', 'S1'),
    ('2026-06-13', 'RONALDO JR', 'S1'),
    ('2026-07-05', 'RONALDO JR', 'S1'),
    ('2026-01-10', 'LUIZ ROBERTO', 'S1'),
    ('2026-01-11', 'LUIZ ROBERTO', 'S2'),
    ('2026-02-07', 'LUIZ ROBERTO', 'S2'),
    ('2026-02-08', 'LUIZ ROBERTO', 'S1'),
    ('2026-03-21', 'LUIZ ROBERTO', 'S2'),
    ('2026-03-22', 'LUIZ ROBERTO', 'S1'),
    ('2026-05-23', 'LUIZ ROBERTO', 'S1'),
    ('2026-05-24', 'LUIZ ROBERTO', 'S2'),
    ('2026-01-03', 'DIONIZIO', 'S2'),
    ('2026-01-04', 'DIONIZIO', 'S1'),
    ('2026-01-17', 'DIONIZIO', 'S2'),
    ('2026-01-18', 'DIONIZIO', 'S1'),
    ('2026-03-07', 'DIONIZIO', 'S2'),
    ('2026-03-08', 'DIONIZIO', 'S1'),
    ('2026-04-04', 'DIONIZIO', 'S2'),
    ('2026-04-11', 'DIONIZIO', 'S2'),
    ('2026-04-12', 'DIONIZIO', 'S1'),
    ('2026-05-01', 'DIONIZIO', 'S2'),
    ('2026-05-02', 'DIONIZIO', 'S2'),
    ('2026-05-03', 'DIONIZIO', 'S1'),
    ('2026-06-21', 'DIONIZIO', 'S1'),
]


class Command(BaseCommand):
    help = 'Importa a planilha CIDIS 2026, preserva historico ate 09/07 e redistribui o restante.'

    def handle(self, *args, **options):
        self.stdout.write('>>> Importando planilha CIDIS 2026 da escala gerencial...')

        self._criar_feriados()
        usuarios = self._atualizar_usuarios()
        self._desativar_usuarios_fora_do_roster()
        call_command('sincronizar_usuarios_padrao')
        self._recriar_bloqueios(usuarios)
        self._atualizar_cargas_iniciais(usuarios)
        self._importar_historico(usuarios)
        self._travar_historico()
        self._limpar_futuro()

        ConfiguracaoSistema.objects.update_or_create(
            chave='data_corte_historico',
            defaults={
                'valor': DATA_CORTE_HISTORICO.isoformat(),
                'descricao': 'A partir desta data a escala usa regra nova de um gerente por dia.',
            },
        )
        ConfiguracaoSistema.objects.update_or_create(
            chave='base_historica',
            defaults={
                'valor': f'{HISTORICO_INICIO.isoformat()} a {IMPORTACAO_HISTORICO_FIM.isoformat()}',
                'descricao': 'Historico CIDIS 2026 contado como base proporcional.',
            },
        )
        ConfiguracaoSistema.objects.update_or_create(
            chave='geracao_futura_inicio',
            defaults={
                'valor': GERACAO_FUTURA_INICIO.isoformat(),
                'descricao': 'Data inicial da redistribuicao apos a importacao CIDIS 2026.',
            },
        )

        self.stdout.write('  [BALANCEANDO] Gerando 10/07/2026 a 12/2026...')
        total, erros = regenerar_apos_data(GERACAO_FUTURA_INICIO)
        _atualizar_contadores_usuarios()

        HistoricoAlteracao.objects.create(
            tipo='REGENERACAO',
            descricao='Importacao CIDIS 2026: roster atual, ferias, buffers e escala futura desde 10/07/2026.',
            dados_novos={
                'usuarios': len(USUARIOS_CIDIS_2026),
                'ex_gerentes_desativados': EX_GERENTES_CIDIS_2026,
                'ferias': len(FERIAS_CIDIS_2026),
                'historico_fim': IMPORTACAO_HISTORICO_FIM.isoformat(),
                'dias_gerados': total,
            },
        )

        self.stdout.write(f'  [OK] {total} dias futuros gerados.')
        for erro in erros:
            self.stdout.write(f'  [WARN] {erro}')

        self.stdout.write(self.style.SUCCESS('[OK] Planilha CIDIS 2026 aplicada.'))

    def _atualizar_usuarios(self):
        grupos = {
            'A': GrupoEscala.objects.get_or_create(nome='A', defaults={'descricao': 'Grupo A'})[0],
            'B': GrupoEscala.objects.get_or_create(nome='B', defaults={'descricao': 'Grupo B'})[0],
        }
        usuarios = {}
        for nome, lotacao, telefone, grupo in USUARIOS_CIDIS_2026:
            usuario = (
                UsuarioEscala.objects.filter(nome=nome).first()
                or UsuarioEscala.objects.filter(codigo_legado=lotacao).first()
            )
            defaults = {
                'nome': nome,
                'codigo_legado': lotacao,
                'lotacao': lotacao,
                'telefone': telefone,
                'grupo': grupos[grupo],
                'ativo': True,
            }
            if usuario:
                for campo, valor in defaults.items():
                    setattr(usuario, campo, valor)
                usuario.save()
            else:
                usuario = UsuarioEscala.objects.create(**defaults)
            usuarios[nome] = usuario
            self.stdout.write(f'  [USUARIO] {nome} ({lotacao}, {telefone})')
        return usuarios

    def _desativar_usuarios_fora_do_roster(self):
        User = get_user_model()
        roster = {nome for nome, _lotacao, _telefone, _grupo in USUARIOS_CIDIS_2026}
        desativados = 0
        for usuario in UsuarioEscala.objects.exclude(nome__in=roster):
            if usuario.ativo:
                usuario.ativo = False
                usuario.save(update_fields=['ativo'])
                desativados += 1
            if usuario.user and not usuario.user.is_superuser:
                usuario.user.is_active = False
                usuario.user.save(update_fields=['is_active'])
        # Also keep old users with these usernames inactive if they exist without a linked manager.
        for nome in EX_GERENTES_CIDIS_2026:
            username = nome.lower().replace(' ', '.')
            User.objects.filter(username=username, is_superuser=False).update(is_active=False)
        self.stdout.write(f'  [OK] Gerentes fora do roster atual desativados: {desativados}.')

    def _recriar_bloqueios(self, usuarios):
        removidos_planilha, _ = BloqueioUsuario.objects.filter(motivo__icontains='planilha').delete()
        removidos_buffer, _ = BloqueioUsuario.objects.filter(
            motivo__startswith=MOTIVO_BUFFER_FERIAS
        ).delete()
        self.stdout.write(
            f'  [LIMPEZA] {removidos_planilha + removidos_buffer} bloqueios de importacao removidos.'
        )
        for nome, inicio, fim in [(n, i, f) for n, i, f in FERIAS_CIDIS_2026]:
            BloqueioUsuario.objects.update_or_create(
                usuario=usuarios[nome],
                tipo='FERIAS',
                data_inicio=date.fromisoformat(inicio),
                data_fim=date.fromisoformat(fim),
                defaults={'motivo': 'Planilha CIDIS 2026'},
            )
        buffers = 0
        for usuario in usuarios.values():
            buffers += len(sincronizar_buffers_ferias_usuario(usuario))
        self.stdout.write(
            f'  [OK] {len(FERIAS_CIDIS_2026)} ferias e {buffers} buffers de fim de semana importados.'
        )

    def _atualizar_cargas_iniciais(self, usuarios):
        pl_por_usuario = Counter(
            nome for data_str, nome, _papel in MARCACOES_TRABALHO_CIDIS_2026
            if date.fromisoformat(data_str) < DATA_CORTE_HISTORICO
        )
        cobertura_historica = set()
        for mes in range(HISTORICO_INICIO.month, HISTORICO_FIM.month + 1):
            for bloco in get_blocos_cobertura(2026, mes):
                cobertura_historica.update(bloco['days'])

        for nome, usuario in usuarios.items():
            ferias_dias = 0
            for blk in BloqueioUsuario.objects.filter(usuario=usuario, tipo='FERIAS'):
                inicio = max(blk.data_inicio, HISTORICO_INICIO)
                fim = min(blk.data_fim, HISTORICO_FIM)
                if inicio <= fim:
                    ferias_dias += (fim - inicio).days + 1

            oportunidades = 0
            for d in cobertura_historica:
                bloqueado = BloqueioUsuario.objects.filter(
                    usuario=usuario, data_inicio__lte=d, data_fim__gte=d
                ).exists()
                if not bloqueado:
                    oportunidades += 1

            usuario.fer_inicial = ferias_dias
            usuario.pl_inicial = pl_por_usuario[nome]
            usuario.oportunidades_iniciais = oportunidades
            usuario.save(update_fields=['fer_inicial', 'pl_inicial', 'oportunidades_iniciais'])
            self.stdout.write(
                f'  [CARGA] {nome}: PL historico={usuario.pl_inicial}, '
                f'oportunidades={usuario.oportunidades_iniciais}, ferias={usuario.fer_inicial}'
            )

    def _importar_historico(self, usuarios):
        EscalaDia.objects.filter(
            data__gte=HISTORICO_INICIO,
            data__lte=IMPORTACAO_HISTORICO_FIM,
        ).delete()

        meta = {}
        for mes in range(1, IMPORTACAO_HISTORICO_FIM.month + 1):
            for bloco in get_blocos_cobertura(2026, mes):
                for d in bloco['days']:
                    meta[d] = bloco['type']

        por_data = defaultdict(list)
        for data_str, nome, papel in MARCACOES_TRABALHO_CIDIS_2026:
            d = date.fromisoformat(data_str)
            if d <= IMPORTACAO_HISTORICO_FIM:
                por_data[d].append((papel, nome))

        prioridade = {'S1': 0, 'S': 1, 'S2': 2}
        importados = 0
        for d in sorted(por_data):
            papel, nome = sorted(por_data[d], key=lambda item: prioridade.get(item[0], 9))[0]
            tipo = meta.get(d)
            EscalaDia.objects.create(
                data=d,
                s1=usuarios[nome],
                s2=None,
                fim_de_semana=d.weekday() in (5, 6),
                feriado=tipo == 'FERIADO',
                feriadao=tipo == 'FERIADAO',
                dia_util=False,
                manual=d >= DATA_CORTE_HISTORICO,
                status='MANUAL' if d >= DATA_CORTE_HISTORICO else 'FECHADA',
                observacao=(
                    f'Historico CIDIS 2026 importado da marcacao {papel}; '
                    'S1/S2 pre-corte contam no PL inicial.'
                ),
            )
            importados += 1
        self.stdout.write(f'  [OK] {importados} dias historicos importados ate 09/07/2026.')

    def _travar_historico(self):
        for mes in range(1, 7):
            MesFechado.objects.update_or_create(
                ano=2026,
                mes=mes,
                defaults={
                    'status': 'BLOQUEADO',
                    'motivo': 'Historico CIDIS 2026 importado ate 30/06/2026.',
                },
            )
            EscalaDia.objects.filter(data__year=2026, data__month=mes).update(status='FECHADA')
        self.stdout.write('  [OK] Jan-Jun/2026 travados como historico.')

    def _limpar_futuro(self):
        MesFechado.objects.filter(ano=2026, mes__gte=7).delete()
        MesFechado.objects.filter(ano__gte=2027).delete()
        EscalaDia.objects.filter(data__gte=GERACAO_FUTURA_INICIO).delete()
        EscalaBloco.objects.filter(data_inicio__gte=DATA_CORTE_HISTORICO).delete()
        self.stdout.write('  [OK] Escala futura desde 10/07/2026 limpa para redistribuicao.')

    def _criar_feriados(self):
        count = 0
        for ano in [2025, 2026, 2027]:
            for mes, dia, nome in FERIADOS_NACIONAIS_FIXOS:
                _, created = Feriado.objects.get_or_create(
                    data=date(ano, mes, dia),
                    nome=nome,
                    defaults={'tipo': 'NACIONAL', 'ativo': True, 'recorrente': True},
                )
                count += int(created)
            for mes, dia, nome in FERIADOS_ESTADUAIS_PR:
                _, created = Feriado.objects.get_or_create(
                    data=date(ano, mes, dia),
                    nome=nome,
                    defaults={'tipo': 'ESTADUAL', 'ativo': True, 'recorrente': True},
                )
                count += int(created)
            for mes, dia, nome in FERIADOS_MUNICIPAIS_CURITIBA:
                _, created = Feriado.objects.get_or_create(
                    data=date(ano, mes, dia),
                    nome=nome,
                    defaults={'tipo': 'MUNICIPAL', 'ativo': True, 'recorrente': True},
                )
                count += int(created)
            for d, nome, tipo in get_feriados_moveis(ano):
                _, created = Feriado.objects.get_or_create(
                    data=d,
                    nome=nome,
                    defaults={'tipo': tipo, 'ativo': True, 'recorrente': False},
                )
                count += int(created)
        self.stdout.write(f'  [OK] Feriados verificados ({count} novos).')
