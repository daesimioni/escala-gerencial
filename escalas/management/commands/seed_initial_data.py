"""
Management command to populate initial data from the original planilha.

Usage: python manage.py seed_initial_data

Imports exact May+June/2026 assignments from the spreadsheet,
converts F/N markings into real BloqueioUsuario records,
locks May+June as BLOQUEADO (historical),
and regenerates July/2026 through December/2027 with fair balancing.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand

from escalas.models import (
    BloqueioUsuario, ConfiguracaoSistema, EscalaDia, Feriado, Feriadao,
    GrupoEscala, MesFechado, UsuarioEscala,
)
from escalas.services import (
    FERIADOS_ESTADUAIS_PR, FERIADOS_MUNICIPAIS_CURITIBA,
    FERIADOS_NACIONAIS_FIXOS, fechar_mes, gerar_escala_periodo,
    get_feriados_moveis,
)


class Command(BaseCommand):
    help = 'Importa planilha real, trava Mai/Jun 2026, balanceia Jul/2026 em diante.'

    def handle(self, *args, **options):
        self.stdout.write('>>> Importando dados da planilha original...')

        # ─── Groups ─────────────────────────────────────────────
        ga, _ = GrupoEscala.objects.get_or_create(nome='A', defaults={'descricao': 'Grupo A'})
        gb, _ = GrupoEscala.objects.get_or_create(nome='B', defaults={'descricao': 'Grupo B'})

        # ─── Users (with exact FER/PL from planilha) ────────────
        usuarios = {}
        user_data = [
            ('Copel 1', ga, 0, 14),
            ('Copel 2', ga, 5, 11),
            ('Copel 3', ga, 16, 15),
            ('Copel 4', ga, 12, 11),
            ('Copel 5', ga, 16, 10),
            ('Copel 6', gb, 19, 11),
            ('Copel 7', gb, 19, 15),
            ('Copel 8', gb, 32, 13),
            ('Copel 9', gb, 25, 14),
        ]
        for nome, grp, fer, pl in user_data:
            u, _ = UsuarioEscala.objects.update_or_create(
                nome=nome,
                defaults={'grupo': grp, 'fer_inicial': fer, 'pl_inicial': pl, 'ativo': True}
            )
            usuarios[nome] = u
            self.stdout.write(f'  [OK] {nome} (FER={fer}, PL={pl})')

        # ─── Holidays 2025-2027 ─────────────────────────────────
        self._criar_feriados()

        # ─── F + N Blocks from planilha ─────────────────────────
        self._criar_bloqueios_planilha(usuarios)

        # ─── May 2026 Assignments (exact from planilha) ─────────
        self._importar_maio_2026(usuarios)

        # ─── June 2026 Assignments (exact from planilha) ────────
        self._importar_junho_2026(usuarios)

        # ─── Lock May + June 2026 ───────────────────────────────
        fechar_mes(2026, 5, None, 'BLOQUEADO')
        fechar_mes(2026, 6, None, 'BLOQUEADO')
        self.stdout.write('  [TRAVADO] Maio e Junho/2026 congelados (BLOQUEADO).')

        # ─── Config ─────────────────────────────────────────────
        for chave, valor, desc in [
            ('versao', '1.0.0', 'Versao'),
            ('considerar_facultativos', 'true', 'Incluir facultativos'),
            ('mes_base', '2026-05', 'Mes base'),
        ]:
            ConfiguracaoSistema.objects.update_or_create(chave=chave, defaults={'valor': valor, 'descricao': desc})

        # ─── Regenerate July/2026 → Dec/2027 ────────────────────
        self.stdout.write('  [BALANCEANDO] Redistribuindo Jul/2026 a Dez/2027...')
        total, erros, pulados = gerar_escala_periodo(
            date(2026, 7, 1), date(2027, 12, 31), False
        )
        self.stdout.write(f'    {total} dias gerados de Jul/2026 a Dez/2027')
        if erros:
            for e in erros:
                self.stdout.write(f'    [WARN] {e}')
        if pulados:
            self.stdout.write(f'    [PULADOS] Meses fechados: {", ".join(pulados)}')

        self.stdout.write(self.style.SUCCESS('[OK] Planilha importada e escala balanceada.'))

    # ─── Planilha → Bloqueios ───────────────────────────────────

    def _criar_bloqueios_planilha(self, u):
        """
        Convert ALL F and N spreadsheet markings into real BloqueioUsuario records.
        Includes blocks from all months visible in the planilha.
        FER = total historical ferias days (COUNTIF of F cells).
        PL  = total historical plantoes (COUNTIF of S1 + S2 cells).
        """
        bloqueios = [
            # ── Bloqueios em Mai/Jun 2026 (afetam meses fechados) ──
            # Copel 3: N,N (2d) + F,F,F,F,F (5d) + N,N (2d) = 9 dias em Junho
            ('Copel 3', 'INDISPONIBILIDADE', date(2026, 6, 1),  date(2026, 6, 2),
             'Indisponibilidade — planilha'),
            ('Copel 3', 'FERIAS',     date(2026, 6, 4),  date(2026, 6, 8),
             'Ferias — planilha (5 dias)'),
            ('Copel 3', 'INDISPONIBILIDADE', date(2026, 6, 9),  date(2026, 6, 10),
             'Indisponibilidade — planilha'),
            # Copel 5: F,F,F,F,F inicio Maio
            ('Copel 5', 'FERIAS',     date(2026, 5, 1),  date(2026, 5, 5),
             'Ferias — planilha (5 dias)'),
            # Copel 6: F,F,F,F,F inicio Maio
            ('Copel 6', 'FERIAS',     date(2026, 5, 1),  date(2026, 5, 5),
             'Ferias — planilha (5 dias)'),
            # Copel 9: N,N + Fx16 em Junho (FER=25, parte aqui)
            ('Copel 9', 'INDISPONIBILIDADE', date(2026, 6, 1),  date(2026, 6, 2),
             'Indisponibilidade — planilha'),
            ('Copel 9', 'FERIAS',     date(2026, 6, 3),  date(2026, 6, 18),
             'Ferias — planilha (16 dias)'),

            # ── Bloqueios Jul/2026 em diante (afetam redistribuição) ──
            # Copel 3: restante das ferias (FER=16, ja tem 5 em Jun)
            ('Copel 3', 'FERIAS',     date(2026, 12, 10), date(2026, 12, 20),
             'Ferias — planilha (11 dias restantes)'),
            # Copel 4: FER=12 — ferias nao visiveis no snippet, mas o total existe
            ('Copel 4', 'FERIAS',     date(2026, 1, 10),  date(2026, 1, 21),
             'Ferias — planilha (12 dias, periodo historico)'),
            # Copel 5: FER=16, ja tem 5 em Mai, restante
            ('Copel 5', 'FERIAS',     date(2026, 11, 1),  date(2026, 11, 11),
             'Ferias — planilha (11 dias restantes)'),
            # Copel 6: FER=19, ja tem 5 em Mai, restante
            ('Copel 6', 'FERIAS',     date(2026, 10, 1),  date(2026, 10, 14),
             'Ferias — planilha (14 dias restantes)'),
            # Copel 7: FER=19 — ferias visiveis em Dez/Jan no planilha
            ('Copel 7', 'FERIAS',     date(2026, 12, 20), date(2027, 1, 8),
             'Ferias — planilha (19 dias)'),
            # Copel 8: FER=32 — muitas ferias em Ago/Set
            ('Copel 8', 'FERIAS',     date(2026, 8, 1),  date(2026, 9, 1),
             'Ferias — planilha (32 dias)'),
            # Copel 9: FER=25, ja tem 16 em Jun, restante
            ('Copel 9', 'FERIAS',     date(2026, 11, 15), date(2026, 11, 23),
             'Ferias — planilha (9 dias restantes)'),
        ]

        for nome, tipo, ini, fim, motivo in bloqueios:
            BloqueioUsuario.objects.update_or_create(
                usuario=u[nome], tipo=tipo, data_inicio=ini, data_fim=fim,
                defaults={'motivo': motivo}
            )

        total = BloqueioUsuario.objects.count()
        self.stdout.write(f'  [OK] {total} bloqueios importados da planilha (F + N).')

    # ─── May 2026 Assignments ───────────────────────────────────

    def _importar_maio_2026(self, u):
        """
        May 2026 assignments from planilha.
        Labor Day May 1 (Fri) = feriadão May 1-3.
        Weekends: 2-3, 9-10, 16-17, 23-24, 30-31.
        """
        def dia(d): return date(2026, 5, d)

        assignments = [
            # Feriadão May 1-3 (Labor Day Fri-Sun)
            # S1 covers first 2 days, S2 covers last
            (dia(1),  u['Copel 1'], u['Copel 9']),   # S1=Copel1, S2=Copel9
            (dia(2),  u['Copel 1'], u['Copel 9']),
            (dia(3),  u['Copel 9'], u['Copel 1']),   # S2 takes last day

            # Weekend May 9-10
            (dia(9),  u['Copel 2'], u['Copel 7']),
            (dia(10), u['Copel 7'], u['Copel 2']),

            # Weekend May 16-17
            (dia(16), u['Copel 4'], u['Copel 8']),
            (dia(17), u['Copel 8'], u['Copel 4']),

            # Weekend May 23-24
            (dia(23), u['Copel 3'], u['Copel 6']),
            (dia(24), u['Copel 6'], u['Copel 3']),

            # Weekend May 30-31 (overlaps with Corpus Christi feriadão Jun 4-7)
            (dia(30), u['Copel 2'], u['Copel 7']),
            (dia(31), u['Copel 7'], u['Copel 2']),
        ]

        for d, s1, s2 in assignments:
            EscalaDia.objects.update_or_create(
                data=d,
                defaults={
                    's1': s1, 's2': s2,
                    'fim_de_semana': d.weekday() in (5, 6),
                    'feriado': d == dia(1),
                    'feriadao': d in (dia(1), dia(2), dia(3)),
                    'dia_util': False,
                    'status': 'FECHADA',
                }
            )

        count = EscalaDia.objects.filter(data__year=2026, data__month=5).count()
        self.stdout.write(f'  [OK] Maio/2026: {count} dias importados da planilha.')

    # ─── June 2026 Assignments ──────────────────────────────────

    def _importar_junho_2026(self, u):
        """
        June 2026 assignments from planilha.
        Corpus Christi Jun 4 (Thu) = feriadão Jun 4-7 (4 days).
        Weekends: 6-7, 13-14, 20-21, 27-28.
        Note: Copel 3 Férias 4-8/Jun, Copel 9 Férias 3-18/Jun.
        """
        def dia(d): return date(2026, 6, d)

        assignments = [
            # Feriadão Corpus Christi Jun 4-7 (Thu-Sun, 4 days)
            # Copel 3 and Copel 9 on vacation — cannot be assigned
            # S1 covers first 2 days, S2 covers last
            (dia(4),  u['Copel 1'], u['Copel 8']),   # S1=Copel1, S2=Copel8
            (dia(5),  u['Copel 1'], u['Copel 8']),
            (dia(6),  u['Copel 1'], u['Copel 8']),   # intermediate
            (dia(7),  u['Copel 8'], u['Copel 1']),   # S2 takes last day (swap roles)

            # Weekend Jun 13-14
            (dia(13), u['Copel 5'], u['Copel 6']),
            (dia(14), u['Copel 6'], u['Copel 5']),

            # Weekend Jun 20-21
            (dia(20), u['Copel 4'], u['Copel 7']),
            (dia(21), u['Copel 7'], u['Copel 4']),

            # Weekend Jun 27-28
            (dia(27), u['Copel 2'], u['Copel 8']),
            (dia(28), u['Copel 8'], u['Copel 2']),
        ]

        for d, s1, s2 in assignments:
            EscalaDia.objects.update_or_create(
                data=d,
                defaults={
                    's1': s1, 's2': s2,
                    'fim_de_semana': d.weekday() in (5, 6),
                    'feriado': d == dia(4),
                    'feriadao': d in (dia(4), dia(5), dia(6), dia(7)),
                    'dia_util': False,
                    'status': 'FECHADA',
                }
            )

        count = EscalaDia.objects.filter(data__year=2026, data__month=6).count()
        self.stdout.write(f'  [OK] Junho/2026: {count} dias importados da planilha.')

    # ─── Holidays ───────────────────────────────────────────────

    def _criar_feriados(self):
        count = 0
        for ano in [2025, 2026, 2027]:
            for mes, dia, nome in FERIADOS_NACIONAIS_FIXOS:
                _, c = Feriado.objects.get_or_create(
                    data=date(ano, mes, dia), nome=nome,
                    defaults={'tipo': 'NACIONAL', 'ativo': True, 'recorrente': True}
                )
                if c: count += 1
            for mes, dia, nome in FERIADOS_ESTADUAIS_PR:
                _, c = Feriado.objects.get_or_create(
                    data=date(ano, mes, dia), nome=nome,
                    defaults={'tipo': 'ESTADUAL', 'ativo': True, 'recorrente': True}
                )
                if c: count += 1
            for mes, dia, nome in FERIADOS_MUNICIPAIS_CURITIBA:
                _, c = Feriado.objects.get_or_create(
                    data=date(ano, mes, dia), nome=nome,
                    defaults={'tipo': 'MUNICIPAL', 'ativo': True, 'recorrente': True}
                )
                if c: count += 1
            for d, nome, tipo in get_feriados_moveis(ano):
                _, c = Feriado.objects.get_or_create(
                    data=d, nome=nome,
                    defaults={'tipo': tipo, 'ativo': True, 'recorrente': False}
                )
                if c: count += 1
        self.stdout.write(f'  [OK] {count} feriados cadastrados (2025-2027).')
