"""
Tests for Escala de Sobreaviso core business logic.
"""
from datetime import date

from django.test import TestCase

from .models import (
    BloqueioUsuario, EscalaDia, Feriado, GrupoEscala, UsuarioEscala,
)
from .services import (
    calcular_pascoa, detectar_feriadoes, encontrar_melhor_par,
    gerar_escala_mensal, get_blocos_cobertura, get_usuarios_disponiveis,
    validar_dia,
)


class EasterCalculationTests(TestCase):
    """Test Easter (Páscoa) calculation."""

    def test_pascoa_2025(self):
        self.assertEqual(calcular_pascoa(2025), date(2025, 4, 20))

    def test_pascoa_2026(self):
        self.assertEqual(calcular_pascoa(2026), date(2026, 4, 5))

    def test_pascoa_2027(self):
        self.assertEqual(calcular_pascoa(2027), date(2027, 3, 28))


class FeriadaoDetectionTests(TestCase):
    """Test feriadão detection logic."""

    def setUp(self):
        # Create groups and users for availability checks
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.grupo_b = GrupoEscala.objects.create(nome='B')
        for i in range(1, 6):
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_a)
        for i in range(6, 10):
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_b)

    def test_detecta_feriadao_corpus_christi_2026(self):
        """Corpus Christi 2026 is Thu Jun 4, should create 4-day feriadão (Thu-Sun)."""
        result = detectar_feriadoes(2026, 6)
        self.assertGreater(len(result['feriadoes']), 0)
        # Verify feriadão covers Jun 4-7
        fd_days = []
        for fd in result['feriadoes']:
            fd_days.extend(fd['days'])
        self.assertIn(date(2026, 6, 4), fd_days)
        self.assertIn(date(2026, 6, 7), fd_days)

    def test_detecta_feriadao_sexta_santa_2026(self):
        """Good Friday 2026 is Apr 3 (Fri), should create 3-day feriadão."""
        result = detectar_feriadoes(2026, 4)
        self.assertGreater(len(result['feriadoes']), 0)

    def test_fim_de_semana_normal(self):
        """Regular weekend without holidays should be detected as weekend."""
        # July 2026 has no holidays — weekends should be plain weekend blocks
        result = detectar_feriadoes(2026, 7)
        self.assertGreater(len(result['fins_de_semana']), 0)
        self.assertEqual(len(result['feriadoes']), 0)

    def test_isolated_holiday(self):
        """Tiradentes 2026 is Tue Apr 21 — should create feriadão with bridge on Mon."""
        result = detectar_feriadoes(2026, 4)
        fd_days = []
        for fd in result['feriadoes']:
            fd_days.extend(fd['days'])
        # Tue Apr 21 + Mon Apr 20 bridge + Sat-Sun Apr 18-19 = 4 days
        self.assertIn(date(2026, 4, 21), fd_days)


class CoverageBlockTests(TestCase):
    """Test coverage block generation."""

    def setUp(self):
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.grupo_b = GrupoEscala.objects.create(nome='B')
        for i in range(1, 6):
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_a)
        for i in range(6, 10):
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_b)

    def test_blocos_maio_2026(self):
        """May 2026 has Labor Day (Fri May 1, feriadão) + 4 regular weekends."""
        blocos = get_blocos_cobertura(2026, 5)
        self.assertGreater(len(blocos), 0)
        types = set(b['type'] for b in blocos)
        self.assertIn('FERIADAO', types)

    def test_blocos_mes_sem_feriados(self):
        """July 2026 has no holidays — only weekend blocks."""
        blocos = get_blocos_cobertura(2026, 7)
        for b in blocos:
            self.assertEqual(b['type'], 'FIM_DE_SEMANA')


class ScaleGenerationTests(TestCase):
    """Test automatic scale generation."""

    def setUp(self):
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.grupo_b = GrupoEscala.objects.create(nome='B')
        self.ua1 = UsuarioEscala.objects.create(nome='Copel 1', grupo=self.grupo_a)
        self.ua2 = UsuarioEscala.objects.create(nome='Copel 2', grupo=self.grupo_a)
        self.ub1 = UsuarioEscala.objects.create(nome='Copel 6', grupo=self.grupo_b)
        self.ub2 = UsuarioEscala.objects.create(nome='Copel 7', grupo=self.grupo_b)

    def test_gera_escala_mensal(self):
        """Generate scale for a month — should create assignments."""
        criados, erros = gerar_escala_mensal(2026, 7, False)
        self.assertGreater(criados, 0)
        self.assertEqual(len(erros), 0)

    def test_todas_duplas_sao_grupos_diferentes(self):
        """Every assignment must have S1 and S2 from different groups."""
        gerar_escala_mensal(2026, 7, False)
        for ed in EscalaDia.objects.filter(data__year=2026, data__month=7):
            if ed.s1 and ed.s2:
                self.assertNotEqual(ed.s1.grupo_id, ed.s2.grupo_id,
                                    f'{ed.data}: S1={ed.s1.nome}, S2={ed.s2.nome} — mesmo grupo!')

    def test_usuarios_bloqueados_nao_escalados(self):
        """Blocked users should never be assigned."""
        # Block Copel 1 for the entire month
        BloqueioUsuario.objects.create(
            usuario=self.ua1,
            tipo='FERIAS',
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 31),
        )
        gerar_escala_mensal(2026, 7, False)
        for ed in EscalaDia.objects.filter(data__year=2026, data__month=7):
            self.assertNotEqual(ed.s1_id, self.ua1.id)
            self.assertNotEqual(ed.s2_id, self.ua1.id)

    def test_preserva_manuais(self):
        """Manual assignments should survive regeneration."""
        data = date(2026, 7, 4)
        EscalaDia.objects.create(
            data=data,
            s1=self.ua2,
            s2=self.ub2,
            manual=True,
            status='MANUAL',
            fim_de_semana=True,
        )
        gerar_escala_mensal(2026, 7, True)
        ed = EscalaDia.objects.get(data=data)
        self.assertEqual(ed.s1_id, self.ua2.id)
        self.assertEqual(ed.s2_id, self.ub2.id)
        self.assertTrue(ed.manual)


class AvailabilityTests(TestCase):
    """Test user availability checking."""

    def setUp(self):
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.grupo_b = GrupoEscala.objects.create(nome='B')
        self.ua1 = UsuarioEscala.objects.create(nome='Copel 1', grupo=self.grupo_a)
        self.ua2 = UsuarioEscala.objects.create(nome='Copel 2', grupo=self.grupo_a)
        self.ub1 = UsuarioEscala.objects.create(nome='Copel 6', grupo=self.grupo_b)

    def test_todos_disponiveis_sem_bloqueios(self):
        disponiveis_a = get_usuarios_disponiveis(date(2026, 7, 4), self.grupo_a)
        self.assertEqual(len(disponiveis_a), 2)

    def test_bloqueado_nao_disponivel(self):
        BloqueioUsuario.objects.create(
            usuario=self.ua1,
            tipo='FERIAS',
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 10),
        )
        disponiveis_a = get_usuarios_disponiveis(date(2026, 7, 4), self.grupo_a)
        self.assertEqual(len(disponiveis_a), 1)
        self.assertEqual(disponiveis_a[0].id, self.ua2.id)

    def test_bloqueio_parcial(self):
        """User should be available before and after block, but not during."""
        BloqueioUsuario.objects.create(
            usuario=self.ua1,
            tipo='TREINAMENTO',
            data_inicio=date(2026, 7, 10),
            data_fim=date(2026, 7, 20),
        )
        # During block
        self.assertEqual(len(get_usuarios_disponiveis(date(2026, 7, 15), self.grupo_a)), 1)
        # Before block
        self.assertEqual(len(get_usuarios_disponiveis(date(2026, 7, 5), self.grupo_a)), 2)
        # After block
        self.assertEqual(len(get_usuarios_disponiveis(date(2026, 7, 25), self.grupo_a)), 2)


class ConflictValidationTests(TestCase):
    """Test conflict detection."""

    def setUp(self):
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.grupo_b = GrupoEscala.objects.create(nome='B')
        self.ua1 = UsuarioEscala.objects.create(nome='Copel 1', grupo=self.grupo_a)
        self.ua2 = UsuarioEscala.objects.create(nome='Copel 2', grupo=self.grupo_a)
        self.ub1 = UsuarioEscala.objects.create(nome='Copel 6', grupo=self.grupo_b)

    def test_mesmo_grupo_gera_erro(self):
        problemas = validar_dia(date(2026, 7, 4), self.ua1, self.ua2)
        erros = [p for p in problemas if p['tipo'] == 'erro']
        self.assertGreater(len(erros), 0)

    def test_grupos_diferentes_sem_erro(self):
        problemas = validar_dia(date(2026, 7, 4), self.ua1, self.ub1)
        erros = [p for p in problemas if p['tipo'] == 'erro']
        self.assertEqual(len(erros), 0)

    def test_bloqueado_gera_erro(self):
        BloqueioUsuario.objects.create(
            usuario=self.ua1,
            tipo='FERIAS',
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 10),
        )
        problemas = validar_dia(date(2026, 7, 4), self.ua1, self.ub1)
        erros = [p for p in problemas if p['tipo'] == 'erro']
        self.assertGreater(len(erros), 0)
