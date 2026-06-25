from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand

from escalas.models import (
    BloqueioUsuario, ConfiguracaoSistema, EscalaBloco, EscalaDia, Feriado,
    GrupoEscala, HistoricoAlteracao, MesFechado, UsuarioEscala,
)
from escalas.services import (
    DATA_CORTE_HISTORICO, FERIADOS_ESTADUAIS_PR, FERIADOS_MUNICIPAIS_CURITIBA,
    FERIADOS_NACIONAIS_FIXOS, HISTORICO_FIM, HISTORICO_INICIO,
    _atualizar_contadores_usuarios, gerar_escala_periodo,
    get_blocos_cobertura, get_feriados_moveis,
)


USUARIOS_PLANILHA = [
    ('Copel 1', 'SAMUEL BITELO', 'DOTR', '41 99826-2343', 'A', 0, 14, 57),
    ('Copel 2', 'HENRY WILLIAM', 'VOTRV', '41 99556-1071', 'A', 5, 9, 57),
    ('Copel 3', 'JEZIEL', 'VOTRM', '41 99131-3791', 'A', 16, 15, 49),
    ('Copel 4', 'PANGARTTE', 'VOPCP', '41 99239-5912', 'A', 12, 11, 55),
    ('Copel 5', 'JULIANO MOSKO', 'VOQTR', '42 99155-4541', 'A', 16, 10, 53),
    ('Copel 6', 'MARCOS VINICIUS', 'VIPOP', '41 99169-4582', 'B', 19, 9, 49),
    ('Copel 7', 'RONALDO JR', 'VAPOP', '41 99694-5975', 'B', 19, 13, 55),
    ('Copel 8', 'LUIZ ROBERTO', 'DDCQ', '43 99191-2359', 'B', 32, 11, 53),
    ('Copel 9', 'DIONIZIO', 'VDSED', '41 98884-7269', 'B', 25, 14, 47),
]


BLOQUEIOS_PLANILHA = [
    ('HENRY WILLIAM', 'FERIAS', '2026-01-12', '2026-01-16'),
    ('JEZIEL', 'FERIAS', '2026-01-01', '2026-01-11'),
    ('JEZIEL', 'INDISPONIBILIDADE', '2026-06-06', '2026-06-07'),
    ('JEZIEL', 'FERIAS', '2026-06-08', '2026-06-12'),
    ('JEZIEL', 'INDISPONIBILIDADE', '2026-06-13', '2026-06-14'),
    ('PANGARTTE', 'FERIAS', '2026-01-19', '2026-01-30'),
    ('JULIANO MOSKO', 'INDISPONIBILIDADE', '2026-01-31', '2026-02-01'),
    ('JULIANO MOSKO', 'FERIAS', '2026-02-02', '2026-02-12'),
    ('JULIANO MOSKO', 'FERIAS', '2026-05-04', '2026-05-08'),
    ('MARCOS VINICIUS', 'FERIAS', '2026-01-26', '2026-01-30'),
    ('MARCOS VINICIUS', 'INDISPONIBILIDADE', '2026-04-18', '2026-04-21'),
    ('MARCOS VINICIUS', 'FERIAS', '2026-04-22', '2026-05-05'),
    ('RONALDO JR', 'FERIAS', '2026-04-06', '2026-04-12'),
    ('RONALDO JR', 'FERIAS', '2026-07-13', '2026-07-24'),
    ('RONALDO JR', 'FERIAS', '2027-01-04', '2027-01-21'),
    ('LUIZ ROBERTO', 'FERIAS', '2026-04-17', '2026-04-17'),
    ('LUIZ ROBERTO', 'FERIAS', '2026-04-20', '2026-04-20'),
    ('LUIZ ROBERTO', 'FERIAS', '2026-06-16', '2026-07-03'),
    ('LUIZ ROBERTO', 'FERIAS', '2026-08-24', '2026-09-04'),
    ('DIONIZIO', 'FERIAS', '2026-02-18', '2026-02-28'),
    ('DIONIZIO', 'INDISPONIBILIDADE', '2026-05-30', '2026-05-31'),
    ('DIONIZIO', 'FERIAS', '2026-06-01', '2026-06-14'),
]


ESCALA_HISTORICA = [
    ('2026-01-03', 'SAMUEL BITELO'),
    ('2026-01-04', 'DIONIZIO'),
    ('2026-01-10', 'LUIZ ROBERTO'),
    ('2026-01-11', 'LUIZ ROBERTO'),
    ('2026-01-17', 'JEZIEL'),
    ('2026-01-18', 'DIONIZIO'),
    ('2026-01-24', 'JULIANO MOSKO'),
    ('2026-01-25', 'HENRY WILLIAM'),
    ('2026-01-31', 'SAMUEL BITELO'),
    ('2026-02-01', 'RONALDO JR'),
    ('2026-02-07', 'JEZIEL'),
    ('2026-02-08', 'LUIZ ROBERTO'),
    ('2026-02-14', 'PANGARTTE'),
    ('2026-02-15', 'RONALDO JR'),
    ('2026-02-17', 'PANGARTTE'),
    ('2026-02-21', 'MARCOS VINICIUS'),
    ('2026-02-22', 'MARCOS VINICIUS'),
    ('2026-02-28', 'SAMUEL BITELO'),
    ('2026-03-01', 'JEZIEL'),
    ('2026-03-07', 'DIONIZIO'),
    ('2026-03-08', 'DIONIZIO'),
    ('2026-03-14', 'PANGARTTE'),
    ('2026-03-15', 'RONALDO JR'),
    ('2026-03-21', 'JULIANO MOSKO'),
    ('2026-03-22', 'LUIZ ROBERTO'),
    ('2026-03-28', 'MARCOS VINICIUS'),
    ('2026-03-29', 'JEZIEL'),
    ('2026-04-03', 'SAMUEL BITELO'),
    ('2026-04-04', 'SAMUEL BITELO'),
    ('2026-04-05', 'SAMUEL BITELO'),
    ('2026-04-11', 'HENRY WILLIAM'),
    ('2026-04-12', 'DIONIZIO'),
    ('2026-04-18', 'JULIANO MOSKO'),
    ('2026-04-19', 'JULIANO MOSKO'),
    ('2026-04-21', 'JEZIEL'),
    ('2026-04-25', 'JEZIEL'),
    ('2026-04-26', 'SAMUEL BITELO'),
    ('2026-05-01', 'HENRY WILLIAM'),
    ('2026-05-02', 'HENRY WILLIAM'),
    ('2026-05-03', 'DIONIZIO'),
    ('2026-05-09', 'PANGARTTE'),
    ('2026-05-10', 'SAMUEL BITELO'),
    ('2026-05-16', 'JEZIEL'),
    ('2026-05-17', 'MARCOS VINICIUS'),
    ('2026-05-23', 'LUIZ ROBERTO'),
    ('2026-05-24', 'RONALDO JR'),
    ('2026-05-30', 'JULIANO MOSKO'),
    ('2026-05-31', 'HENRY WILLIAM'),
    ('2026-06-04', 'MARCOS VINICIUS'),
    ('2026-06-06', 'MARCOS VINICIUS'),
    ('2026-06-07', 'LUIZ ROBERTO'),
    ('2026-06-13', 'PANGARTTE'),
    ('2026-06-14', 'RONALDO JR'),
    ('2026-06-20', 'JEZIEL'),
    ('2026-06-21', 'DIONIZIO'),
    ('2026-06-27', 'JULIANO MOSKO'),
    ('2026-06-28', 'SAMUEL BITELO'),
]


class Command(BaseCommand):
    help = 'Importa a planilha atual, trava Jan-Jun/2026 e redistribui de Jul/2026 em diante.'

    def handle(self, *args, **options):
        self.stdout.write('>>> Importando planilha atual da escala gerencial...')

        self._criar_feriados()
        usuarios = self._atualizar_usuarios()
        call_command('sincronizar_usuarios_padrao')
        self._recriar_bloqueios(usuarios)
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
                'valor': f'{HISTORICO_INICIO.isoformat()} a {HISTORICO_FIM.isoformat()}',
                'descricao': 'Historico da planilha contado como base proporcional.',
            },
        )

        self.stdout.write('  [BALANCEANDO] Gerando Jul/2026 a Dez/2027...')
        total, erros, pulados = gerar_escala_periodo(date(2026, 7, 1), date(2027, 12, 31), False)
        _atualizar_contadores_usuarios()

        HistoricoAlteracao.objects.create(
            tipo='REGENERACAO',
            descricao='Importacao da planilha atual: usuarios reais, contatos, ferias e escala futura desde 01/07/2026.',
            dados_novos={
                'usuarios': len(USUARIOS_PLANILHA),
                'bloqueios': len(BLOQUEIOS_PLANILHA),
                'historico_dias': len(ESCALA_HISTORICA),
                'dias_gerados': total,
            },
        )

        self.stdout.write(f'  [OK] {total} dias futuros gerados.')
        if pulados:
            self.stdout.write(f'  [PULADOS] {", ".join(pulados)}')
        for erro in erros:
            self.stdout.write(f'  [WARN] {erro}')

        self.stdout.write(self.style.SUCCESS('[OK] Planilha atual aplicada.'))

    def _atualizar_usuarios(self):
        grupos = {
            'A': GrupoEscala.objects.get_or_create(nome='A', defaults={'descricao': 'Grupo A'})[0],
            'B': GrupoEscala.objects.get_or_create(nome='B', defaults={'descricao': 'Grupo B'})[0],
        }
        usuarios = {}
        for codigo, nome, lotacao, telefone, grupo, fer, pl, oportunidades in USUARIOS_PLANILHA:
            usuario = (
                UsuarioEscala.objects.filter(codigo_legado=codigo).first()
                or UsuarioEscala.objects.filter(nome=codigo).first()
                or UsuarioEscala.objects.filter(nome=nome).first()
            )
            defaults = {
                'nome': nome,
                'codigo_legado': codigo,
                'lotacao': lotacao,
                'telefone': telefone,
                'grupo': grupos[grupo],
                'fer_inicial': fer,
                'pl_inicial': pl,
                'oportunidades_iniciais': oportunidades,
                'ativo': True,
            }
            if usuario:
                for campo, valor in defaults.items():
                    setattr(usuario, campo, valor)
                usuario.save()
            else:
                usuario = UsuarioEscala.objects.create(**defaults)
            usuarios[nome] = usuario
            self.stdout.write(f'  [USUARIO] {codigo} -> {nome} ({lotacao}, {telefone})')
        return usuarios

    def _recriar_bloqueios(self, usuarios):
        removidos, _ = BloqueioUsuario.objects.filter(motivo__icontains='planilha').delete()
        self.stdout.write(f'  [LIMPEZA] {removidos} bloqueios de planilha removidos.')
        for nome, tipo, inicio, fim in BLOQUEIOS_PLANILHA:
            BloqueioUsuario.objects.update_or_create(
                usuario=usuarios[nome],
                tipo=tipo,
                data_inicio=date.fromisoformat(inicio),
                data_fim=date.fromisoformat(fim),
                defaults={'motivo': 'Planilha atual'},
            )
        self.stdout.write(f'  [OK] {len(BLOQUEIOS_PLANILHA)} bloqueios importados.')

    def _importar_historico(self, usuarios):
        EscalaDia.objects.filter(data__gte=HISTORICO_INICIO, data__lte=HISTORICO_FIM).delete()
        meta = {}
        for mes in range(1, 7):
            for bloco in get_blocos_cobertura(2026, mes):
                for d in bloco['days']:
                    meta[d] = bloco['type']

        for data_str, nome in ESCALA_HISTORICA:
            d = date.fromisoformat(data_str)
            tipo = meta.get(d)
            EscalaDia.objects.create(
                data=d,
                s1=usuarios[nome],
                s2=None,
                fim_de_semana=d.weekday() in (5, 6),
                feriado=tipo == 'FERIADO',
                feriadao=tipo == 'FERIADAO',
                dia_util=False,
                manual=False,
                status='FECHADA',
                observacao='Historico convertido da planilha antiga; S1/S2 contam no PL inicial.',
            )
        self.stdout.write(f'  [OK] {len(ESCALA_HISTORICA)} dias historicos importados.')

    def _travar_historico(self):
        for mes in range(1, 7):
            MesFechado.objects.update_or_create(
                ano=2026,
                mes=mes,
                defaults={
                    'status': 'BLOQUEADO',
                    'motivo': 'Historico importado da planilha ate 30/06/2026.',
                },
            )
            EscalaDia.objects.filter(data__year=2026, data__month=mes).update(status='FECHADA')
        self.stdout.write('  [OK] Jan-Jun/2026 travados como historico.')

    def _limpar_futuro(self):
        MesFechado.objects.filter(ano=2026, mes__gte=7).delete()
        MesFechado.objects.filter(ano__gte=2027).delete()
        EscalaDia.objects.filter(data__gte=DATA_CORTE_HISTORICO, manual=False).delete()
        EscalaBloco.objects.filter(data_inicio__gte=DATA_CORTE_HISTORICO).delete()
        self.stdout.write('  [OK] Escala futura limpa para redistribuicao.')

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
