"""
Tests for Escala de Sobreaviso core business logic.
"""
from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils.html import strip_tags

from .models import BloqueioUsuario, EscalaDia, GrupoEscala, UsuarioEscala
from .services import (
    calcular_pascoa, detectar_feriadoes, gerar_escala_mensal,
    get_blocos_cobertura, get_usuarios_disponiveis, validar_dia,
)


class EasterCalculationTests(TestCase):
    def test_pascoa_2025(self):
        self.assertEqual(calcular_pascoa(2025), date(2025, 4, 20))

    def test_pascoa_2026(self):
        self.assertEqual(calcular_pascoa(2026), date(2026, 4, 5))

    def test_pascoa_2027(self):
        self.assertEqual(calcular_pascoa(2027), date(2027, 3, 28))


class FeriadaoDetectionTests(TestCase):
    def setUp(self):
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.grupo_b = GrupoEscala.objects.create(nome='B')
        for i in range(1, 6):
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_a)
        for i in range(6, 10):
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_b)

    def test_detecta_feriadao_corpus_christi_2026(self):
        result = detectar_feriadoes(2026, 6)
        fd_days = []
        for fd in result['feriadoes']:
            fd_days.extend(fd['days'])
        self.assertIn(date(2026, 6, 4), fd_days)
        self.assertIn(date(2026, 6, 7), fd_days)

    def test_detecta_feriadao_sexta_santa_2026(self):
        result = detectar_feriadoes(2026, 4)
        self.assertGreater(len(result['feriadoes']), 0)

    def test_fim_de_semana_normal(self):
        result = detectar_feriadoes(2026, 7)
        self.assertGreater(len(result['fins_de_semana']), 0)
        self.assertEqual(len(result['feriadoes']), 0)

    def test_isolated_holiday(self):
        result = detectar_feriadoes(2026, 4)
        fd_days = []
        for fd in result['feriadoes']:
            fd_days.extend(fd['days'])
        self.assertIn(date(2026, 4, 21), fd_days)


class CoverageBlockTests(TestCase):
    def setUp(self):
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.grupo_b = GrupoEscala.objects.create(nome='B')
        for i in range(1, 6):
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_a)
        for i in range(6, 10):
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_b)

    def test_blocos_maio_2026(self):
        blocos = get_blocos_cobertura(2026, 5)
        self.assertGreater(len(blocos), 0)
        self.assertIn('FERIADAO', {b['type'] for b in blocos})

    def test_blocos_mes_sem_feriados(self):
        blocos = get_blocos_cobertura(2026, 7)
        for b in blocos:
            self.assertEqual(b['type'], 'FIM_DE_SEMANA')


class ScaleGenerationTests(TestCase):
    def setUp(self):
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.grupo_b = GrupoEscala.objects.create(nome='B')
        self.usuarios = [
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_a if i <= 5 else self.grupo_b)
            for i in range(1, 10)
        ]
        self.ua1 = self.usuarios[0]
        self.ua2 = self.usuarios[1]

    def test_gera_escala_mensal_com_um_gerente_por_dia(self):
        criados, erros = gerar_escala_mensal(2026, 7, False)
        self.assertGreater(criados, 0)
        self.assertEqual(erros, [])
        for ed in EscalaDia.objects.filter(data__year=2026, data__month=7):
            self.assertIsNotNone(ed.s1)
            self.assertIsNone(ed.s2)

    def test_nao_repete_mesmo_gerente_em_dias_consecutivos(self):
        gerar_escala_mensal(2026, 7, False)
        escalas = list(EscalaDia.objects.filter(data__year=2026, data__month=7).order_by('data'))
        for atual, prox in zip(escalas, escalas[1:]):
            if (prox.data - atual.data).days == 1:
                self.assertNotEqual(atual.s1_id, prox.s1_id)

    def test_usuarios_bloqueados_nao_escalados(self):
        BloqueioUsuario.objects.create(
            usuario=self.ua1,
            tipo='FERIAS',
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 31),
        )
        gerar_escala_mensal(2026, 7, False)
        for ed in EscalaDia.objects.filter(data__year=2026, data__month=7):
            self.assertNotEqual(ed.s1_id, self.ua1.id)

    def test_preserva_manuais(self):
        data = date(2026, 7, 4)
        EscalaDia.objects.create(
            data=data,
            s1=self.ua2,
            manual=True,
            status='MANUAL',
            fim_de_semana=True,
        )
        gerar_escala_mensal(2026, 7, True)
        ed = EscalaDia.objects.get(data=data)
        self.assertEqual(ed.s1_id, self.ua2.id)
        self.assertIsNone(ed.s2)
        self.assertTrue(ed.manual)

    def test_ferias_nao_criam_compensacao_bruta(self):
        gerente_ferias = self.usuarios[0]
        BloqueioUsuario.objects.create(
            usuario=gerente_ferias,
            tipo='FERIAS',
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 15),
        )
        gerar_escala_mensal(2026, 7, False)
        total_ferias = EscalaDia.objects.filter(s1=gerente_ferias).count()
        maior_outro = max(
            EscalaDia.objects.filter(s1=u).count()
            for u in self.usuarios
            if u != gerente_ferias
        )
        self.assertLessEqual(total_ferias, maior_outro)

    def test_feriados_nacional_municipal_estadual_tem_sobreaviso(self):
        for ano, mes in [(2026, 9), (2026, 12)]:
            gerar_escala_mensal(ano, mes, False)

        datas_feriado = [
            date(2026, 9, 7),   # Independencia do Brasil
            date(2026, 9, 8),   # Nossa Senhora da Luz dos Pinhais - Curitiba
            date(2026, 12, 19), # Emancipacao Politica do Parana
        ]
        for data_feriado in datas_feriado:
            with self.subTest(data=data_feriado):
                escala = EscalaDia.objects.filter(data=data_feriado).first()
                self.assertIsNotNone(escala)
                self.assertIsNotNone(escala.s1)
                self.assertIsNone(escala.s2)


class AvailabilityTests(TestCase):
    def setUp(self):
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.ua1 = UsuarioEscala.objects.create(nome='Copel 1', grupo=self.grupo_a)
        self.ua2 = UsuarioEscala.objects.create(nome='Copel 2', grupo=self.grupo_a)

    def test_todos_disponiveis_sem_bloqueios(self):
        disponiveis = get_usuarios_disponiveis(date(2026, 7, 4), self.grupo_a)
        self.assertEqual(len(disponiveis), 2)

    def test_bloqueado_nao_disponivel(self):
        BloqueioUsuario.objects.create(
            usuario=self.ua1,
            tipo='FERIAS',
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 10),
        )
        disponiveis = get_usuarios_disponiveis(date(2026, 7, 4), self.grupo_a)
        self.assertEqual(disponiveis, [self.ua2])

    def test_bloqueio_parcial(self):
        BloqueioUsuario.objects.create(
            usuario=self.ua1,
            tipo='TREINAMENTO',
            data_inicio=date(2026, 7, 10),
            data_fim=date(2026, 7, 20),
        )
        self.assertEqual(len(get_usuarios_disponiveis(date(2026, 7, 15), self.grupo_a)), 1)
        self.assertEqual(len(get_usuarios_disponiveis(date(2026, 7, 5), self.grupo_a)), 2)
        self.assertEqual(len(get_usuarios_disponiveis(date(2026, 7, 25), self.grupo_a)), 2)


class ConflictValidationTests(TestCase):
    def setUp(self):
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.ua1 = UsuarioEscala.objects.create(nome='Copel 1', grupo=self.grupo_a)
        self.ua2 = UsuarioEscala.objects.create(nome='Copel 2', grupo=self.grupo_a)

    def test_mesmo_grupo_nao_gera_erro(self):
        problemas = validar_dia(date(2026, 7, 4), self.ua1, None)
        self.assertEqual([p for p in problemas if p['tipo'] == 'erro'], [])

    def test_bloqueado_gera_erro(self):
        BloqueioUsuario.objects.create(
            usuario=self.ua1,
            tipo='FERIAS',
            data_inicio=date(2026, 7, 1),
            data_fim=date(2026, 7, 10),
        )
        problemas = validar_dia(date(2026, 7, 4), self.ua1, None)
        self.assertGreater(len([p for p in problemas if p['tipo'] == 'erro']), 0)

    def test_dia_consecutivo_gera_erro(self):
        EscalaDia.objects.create(data=date(2026, 7, 4), s1=self.ua1, fim_de_semana=True)
        problemas = validar_dia(date(2026, 7, 5), self.ua1, None)
        self.assertGreater(len([p for p in problemas if p['tipo'] == 'erro']), 0)


class WorkflowViewTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(self.admin_user)
        self.grupo_a = GrupoEscala.objects.create(nome='A')
        self.grupo_b = GrupoEscala.objects.create(nome='B')
        self.usuarios = [
            UsuarioEscala.objects.create(nome=f'Copel {i}', grupo=self.grupo_a if i <= 5 else self.grupo_b)
            for i in range(1, 10)
        ]

    def test_exportacao_mensal_nao_expoe_s1_s2(self):
        gerar_escala_mensal(2026, 7, False)

        response = self.client.get(reverse('exportar_csv'), {'ano': 2026, 'mes': 7})
        self.assertEqual(response.status_code, 200)

        csv_text = response.content.decode('utf-8-sig')
        header = csv_text.splitlines()[0]
        self.assertIn('Gerente de Sobreaviso', header)
        self.assertNotIn('S1', header)
        self.assertNotIn('S2', header)

    def test_cadastro_de_ferias_regenera_sem_sobrecarregar_retorno(self):
        gerente = self.usuarios[0]

        response = self.client.post(reverse('adicionar_bloqueio'), {
            'usuario': gerente.id,
            'tipo': 'FERIAS',
            'data_inicio': '2026-07-01',
            'data_fim': '2026-07-15',
            'motivo': 'Ferias de teste',
        })
        self.assertEqual(response.status_code, 302)

        escalas_ferias = EscalaDia.objects.filter(
            data__gte=date(2026, 7, 1),
            data__lte=date(2026, 7, 15),
        )
        escalas_mes = EscalaDia.objects.filter(data__year=2026, data__month=7)
        self.assertGreater(escalas_mes.count(), 0)
        self.assertFalse(escalas_ferias.filter(s1=gerente).exists())
        self.assertFalse(escalas_mes.exclude(s2=None).exists())

        total_gerente = escalas_mes.filter(s1=gerente).count()
        maior_outro = max(
            escalas_mes.filter(s1=u).count()
            for u in self.usuarios
            if u != gerente
        )
        self.assertLessEqual(total_gerente, maior_outro)

    def test_paginas_principais_nao_mostram_s1_s2_ou_presencial(self):
        gerar_escala_mensal(2026, 7, False)
        paths = [
            reverse('dashboard'),
            reverse('calendario_mes', kwargs={'ano': 2026, 'mes': 7}),
            reverse('calendario_anual', kwargs={'ano': 2026}),
            reverse('bloqueios'),
            reverse('adicionar_bloqueio'),
            reverse('gerar_escala'),
            reverse('trocar_escala'),
            reverse('relatorios'),
            reverse('exportar'),
            reverse('editar_dia', kwargs={'ano': 2026, 'mes': 7, 'dia': 4}),
        ]

        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode('utf-8')
                visible_text = ' '.join(strip_tags(html).split())
                self.assertNotIn('S1', visible_text)
                self.assertNotIn('S2', visible_text)
                self.assertNotIn('presencial', visible_text.lower())

    def test_calendario_mostra_apenas_gerente_escalado_no_dia(self):
        BloqueioUsuario.objects.create(
            usuario=self.usuarios[2],
            tipo='FERIAS',
            data_inicio=date(2026, 7, 4),
            data_fim=date(2026, 7, 4),
        )
        BloqueioUsuario.objects.create(
            usuario=self.usuarios[3],
            tipo='INDISPONIBILIDADE',
            data_inicio=date(2026, 7, 4),
            data_fim=date(2026, 7, 4),
        )
        gerar_escala_mensal(2026, 7, False)

        response = self.client.get(reverse('calendario_mes', kwargs={'ano': 2026, 'mes': 7}))
        self.assertEqual(response.status_code, 200)

        visible_text = ' '.join(strip_tags(response.content.decode('utf-8')).split())
        self.assertIn('Sobreaviso', visible_text)
        self.assertNotIn('F Copel', visible_text)
        self.assertNotIn('N Copel', visible_text)
