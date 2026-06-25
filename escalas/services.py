"""
Core business logic for on-call schedule generation.

Handles: holiday detection, feriadão detection, user scoring,
monthly/yearly scale generation, and redistribution after changes.
"""
import math
from collections import defaultdict
from datetime import date, timedelta

from django.db import models as dm
from django.utils import timezone

from .models import (
    AlertaSistema, BloqueioUsuario, ConfiguracaoSistema, EscalaBloco,
    EscalaDia, Feriado, Feriadao, GrupoEscala, MesFechado, UsuarioEscala,
)

HISTORICO_INICIO = date(2026, 1, 1)
HISTORICO_FIM = date(2026, 6, 30)
DATA_CORTE_HISTORICO = date(2026, 7, 1)


# ─── Holiday Data ───────────────────────────────────────────────────────────

FERIADOS_NACIONAIS_FIXOS = [
    # (mês, dia, nome)
    (1, 1, 'Confraternização Universal'),
    (4, 21, 'Tiradentes'),
    (5, 1, 'Dia do Trabalho'),
    (9, 7, 'Independência do Brasil'),
    (10, 12, 'Nossa Senhora Aparecida'),
    (11, 2, 'Finados'),
    (11, 15, 'Proclamação da República'),
    (11, 20, 'Consciência Negra'),
    (12, 25, 'Natal'),
]

FERIADOS_ESTADUAIS_PR = [
    (12, 19, 'Emancipação Política do Paraná'),
]

FERIADOS_MUNICIPAIS_CURITIBA = [
    (3, 29, 'Aniversário de Curitiba'),
    (9, 8, 'Nossa Senhora da Luz dos Pinhais'),
]


# ─── Easter Calculation (Gauss algorithm) ────────────────────────────────────

def calcular_pascoa(ano):
    """Return Easter Sunday date for a given year (Gauss algorithm, Gregorian)."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def get_feriados_moveis(ano):
    """Return movable holidays for a given year based on Easter."""
    pascoa = calcular_pascoa(ano)
    carnaval_terca = pascoa - timedelta(days=47)
    carnaval_segunda = carnaval_terca - timedelta(days=1)
    sexta_santa = pascoa - timedelta(days=2)
    corpus_christi = pascoa + timedelta(days=60)
    return [
        (carnaval_segunda, 'Carnaval (Segunda-feira)', 'FACULTATIVO'),
        (carnaval_terca, 'Carnaval (Terça-feira)', 'FACULTATIVO'),
        (sexta_santa, 'Sexta-feira Santa', 'NACIONAL'),
        (corpus_christi, 'Corpus Christi', 'FACULTATIVO'),
    ]


# ─── Feriadão Detection ─────────────────────────────────────────────────────

def get_feriados_ativos_no_ano(ano):
    """Return all active holidays for a year as a set of dates."""
    feriados_datas = set()

    # Fixed national holidays
    for mes, dia, nome in FERIADOS_NACIONAIS_FIXOS:
        feriados_datas.add(date(ano, mes, dia))

    # Fixed state holidays
    for mes, dia, nome in FERIADOS_ESTADUAIS_PR:
        feriados_datas.add(date(ano, mes, dia))

    # Fixed municipal holidays
    for mes, dia, nome in FERIADOS_MUNICIPAIS_CURITIBA:
        feriados_datas.add(date(ano, mes, dia))

    # Movable holidays
    for d, nome, tipo in get_feriados_moveis(ano):
        feriados_datas.add(d)

    # DB overrides: active manual/disabled holidays
    db_feriados = Feriado.objects.filter(data__year=ano, ativo=True)
    for f in db_feriados:
        feriados_datas.add(f.data)

    # Remove DB-disabled holidays
    db_inativos = Feriado.objects.filter(data__year=ano, ativo=False)
    for f in db_inativos:
        feriados_datas.discard(f.data)

    return feriados_datas


def is_fim_de_semana(d):
    """Check if date is Saturday (5) or Sunday (6)."""
    return d.weekday() in (5, 6)


# ─── Month Locking ───────────────────────────────────────────────────────────

def is_mes_fechado(ano, mes):
    """Check if a month is locked/closed — auto-generation cannot modify it."""
    return MesFechado.objects.filter(ano=ano, mes=mes).exists()


def get_meses_fechados():
    """Return set of (ano, mes) tuples for all locked months."""
    return set(
        MesFechado.objects.values_list('ano', 'mes')
    )


def fechar_mes(ano, mes, usuario=None, status='FECHADO'):
    """Lock a month — mark all its automatic days as FECHADA and prevent regeneration."""
    mf, created = MesFechado.objects.get_or_create(
        ano=ano, mes=mes,
        defaults={'fechado_por': usuario, 'status': status}
    )
    # Update all EscalaDia in this month to FECHADA status
    EscalaDia.objects.filter(data__year=ano, data__month=mes).update(status='FECHADA')
    return mf, created


def reabrir_mes(ano, mes):
    """Unlock a month — allow it to be regenerated again."""
    MesFechado.objects.filter(ano=ano, mes=mes).delete()
    # Reset FECHADA days back to AUTOMATICA (only those that weren't manually set)
    EscalaDia.objects.filter(
        data__year=ano, data__month=mes, status='FECHADA'
    ).update(status='AUTOMATICA')
    return True


def get_meses_fechados_no_periodo(inicio, fim):
    """Return sorted list of locked (ano, mes) in a date range."""
    fechados = set()
    for mf in MesFechado.objects.all():
        key = (mf.ano, mf.mes)
        # Check if this month overlaps with the period
        mes_inicio = date(mf.ano, mf.mes, 1)
        if mf.mes == 12:
            mes_fim = date(mf.ano + 1, 1, 1) - timedelta(days=1)
        else:
            mes_fim = date(mf.ano, mf.mes + 1, 1) - timedelta(days=1)
        if mes_fim >= inicio and mes_inicio <= fim:
            fechados.add(key)
    return sorted(fechados)


# ─── Pontuação (Enhanced) ───────────────────────────────────────────────────


def detectar_feriadoes(ano, mes):
    """
    Detect long-weekend blocks (feriadões) for a given month.

    Strategy:
    1. Mark all weekends + holidays in range (month ± buffer).
    2. Add emenda (bridge) days: holiday on Tue → Mon is bridge,
       holiday on Thu → Fri is bridge.
    3. Find consecutive runs → classify as feriadão, weekend, or isolated holiday.

    Returns: {
        'feriadoes': [{days: [date,...], nome: str}],
        'fins_de_semana': [[date,...]],
        'feriados_isolados': [date]
    }
    """
    feriados_ano = get_feriados_ativos_no_ano(ano)

    # Date range: target month plus buffer
    primeiro_dia = date(ano, mes, 1)
    if mes == 12:
        ultimo_dia = date(ano + 1, 1, 1) - timedelta(days=1)
    else:
        ultimo_dia = date(ano, mes + 1, 1) - timedelta(days=1)

    inicio = primeiro_dia - timedelta(days=10)
    fim = ultimo_dia + timedelta(days=10)

    # Mark each day
    marcacoes = {}
    cursor = inicio
    while cursor <= fim:
        eh_fds = is_fim_de_semana(cursor)
        eh_feriado = cursor in feriados_ano
        marcacoes[cursor] = {
            'fim_de_semana': eh_fds,
            'feriado': eh_feriado,
            'ponte': False,
        }
        cursor += timedelta(days=1)

    # Apply emenda (bridge) rule
    for d in list(marcacoes.keys()):
        if marcacoes[d]['feriado']:
            dow = d.weekday()
            if dow == 1:  # Tuesday → Monday is bridge
                ponte = d - timedelta(days=1)
                if ponte in marcacoes and not marcacoes[ponte]['fim_de_semana'] and not marcacoes[ponte]['feriado']:
                    marcacoes[ponte]['ponte'] = True
            elif dow == 3:  # Thursday → Friday is bridge
                ponte = d + timedelta(days=1)
                if ponte in marcacoes and not marcacoes[ponte]['fim_de_semana'] and not marcacoes[ponte]['feriado']:
                    marcacoes[ponte]['ponte'] = True

    # Find consecutive runs
    sorted_dates = sorted(marcacoes.keys())
    runs = []
    current = []

    for d in sorted_dates:
        m = marcacoes[d]
        if m['fim_de_semana'] or m['feriado'] or m['ponte']:
            current.append(d)
        else:
            if current:
                runs.append(current)
                current = []
    if current:
        runs.append(current)

    # Classify runs
    feriadoes = []
    fins_de_semana = []
    feriados_isolados = []

    for run in runs:
        tem_feriado = any(marcacoes[d]['feriado'] for d in run)
        tem_fds = any(marcacoes[d]['fim_de_semana'] for d in run)

        if tem_feriado and len(run) >= 2:
            nomes = []
            for d in run:
                if marcacoes[d]['feriado']:
                    nome = next((f.nome for f in Feriado.objects.filter(data=d, ativo=True)), None)
                    if not nome:
                        # Check built-in
                        for mes_f, dia_f, nome_f in FERIADOS_NACIONAIS_FIXOS:
                            if d.month == mes_f and d.day == dia_f:
                                nome = nome_f
                                break
                    if not nome:
                        nome = 'Feriado'
                    nomes.append(nome)
            label = ' / '.join(nomes[:2])
            if len(nomes) > 2:
                label += f' +{len(nomes) - 2}'

            # Filter days in target month
            dias_mes = [d for d in run if d.month == mes and d.year == ano]
            feriadoes.append({'days': dias_mes, 'nome': label, 'all_days': run})

        elif tem_feriado and len(run) == 1:
            feriados_isolados.append(run[0])
        else:
            dias_mes = [d for d in run if d.month == mes and d.year == ano]
            if dias_mes:
                fins_de_semana.append(dias_mes)

    return {
        'feriadoes': feriadoes,
        'fins_de_semana': fins_de_semana,
        'feriados_isolados': feriados_isolados,
    }


# ─── Coverage Blocks ─────────────────────────────────────────────────────────

def get_blocos_cobertura(ano, mes):
    """
    Return all coverage blocks for a month, sorted by start date.
    Each block: {days: [date], type: 'FERIADAO'|'FIM_DE_SEMANA'|'FERIADO', nome: str}
    """
    deteccao = detectar_feriadoes(ano, mes)
    blocos = []

    # Feriadão blocks
    for fd in deteccao['feriadoes']:
        if fd['days']:
            blocos.append({
                'days': sorted(fd['days']),
                'type': 'FERIADAO',
                'nome': fd['nome'],
            })

    # Isolated holidays
    feriadao_days = set()
    for fd in deteccao['feriadoes']:
        feriadao_days.update(fd['days'])

    for d in deteccao['feriados_isolados']:
        if d.month == mes and d.year == ano and d not in feriadao_days:
            blocos.append({
                'days': [d],
                'type': 'FERIADO',
                'nome': get_nome_feriado(d),
            })

    # Weekend blocks not already covered by feriadões
    for fds_days in deteccao['fins_de_semana']:
        uncovered = [d for d in fds_days if d not in feriadao_days]
        if uncovered:
            # Split into consecutive sub-runs
            sub_runs = []
            cur = []
            for d in sorted(uncovered):
                if not cur or (d - cur[-1]).days == 1:
                    cur.append(d)
                else:
                    sub_runs.append(cur)
                    cur = [d]
            if cur:
                sub_runs.append(cur)

            for sr in sub_runs:
                blocos.append({
                    'days': sr,
                    'type': 'FIM_DE_SEMANA',
                    'nome': 'Fim de Semana' if len(sr) == 2 else 'FDS Parcial',
                })

    blocos.sort(key=lambda b: b['days'][0])
    return blocos


def get_nome_feriado(d):
    """Get holiday name for a date."""
    f = Feriado.objects.filter(data=d, ativo=True).first()
    if f:
        return f.nome
    # Check built-in
    for mes, dia, nome in FERIADOS_NACIONAIS_FIXOS:
        if d.month == mes and d.day == dia:
            return nome
    for mes, dia, nome in FERIADOS_ESTADUAIS_PR:
        if d.month == mes and d.day == dia:
            return nome
    for mes, dia, nome in FERIADOS_MUNICIPAIS_CURITIBA:
        if d.month == mes and d.day == dia:
            return nome
    return 'Feriado'


# ─── User Availability ───────────────────────────────────────────────────────

def get_usuarios_disponiveis(d, grupo=None):
    """Return active users not blocked on the given date."""
    qs = UsuarioEscala.objects.filter(ativo=True)
    if grupo:
        qs = qs.filter(grupo=grupo)

    usuarios = list(qs)
    disponiveis = []
    for u in usuarios:
        bloqueado = BloqueioUsuario.objects.filter(
            usuario=u, data_inicio__lte=d, data_fim__gte=d
        ).exists()
        if not bloqueado:
            disponiveis.append(u)
    return disponiveis


def _usuario_disponivel(usuario, d):
    """Return True when the user has no block/vacation on the date."""
    return not BloqueioUsuario.objects.filter(
        usuario=usuario, data_inicio__lte=d, data_fim__gte=d
    ).exists()


def _gerente_do_dia(d):
    """Return the scheduled on-call manager for a date, if any."""
    escala = EscalaDia.objects.filter(data=d).select_related('s1').first()
    return escala.s1 if escala else None


def _tem_escala_consecutiva(usuario, d, atribuicoes_temp=None):
    """Prevent the same manager from being assigned on adjacent dates."""
    atribuicoes_temp = atribuicoes_temp or {}
    for adj in (d - timedelta(days=1), d + timedelta(days=1)):
        temp = atribuicoes_temp.get(adj)
        if temp and temp.id == usuario.id:
            return True
        gerente = _gerente_do_dia(adj)
        if gerente and gerente.id == usuario.id:
            return True
    return False


def get_dias_desde_ultima_escala(usuario, data_ref):
    """Days since user's last assignment."""
    ultima = EscalaDia.objects.filter(
        s1=usuario,
        data__lt=data_ref,
    ).order_by('-data').first()
    if ultima:
        return (data_ref - ultima.data).days
    return 999  # Never assigned — very favorable


def get_bloqueios_proximos(usuario, data_ref, margem=3):
    """Check if user has blocks starting or ending within `margem` days of data_ref."""
    inicio_prox = data_ref
    fim_prox = data_ref + timedelta(days=margem)
    inicio_ant = data_ref - timedelta(days=margem)
    fim_ant = data_ref

    # Block starts soon
    starts = BloqueioUsuario.objects.filter(
        usuario=usuario,
        data_inicio__gte=inicio_prox,
        data_inicio__lte=fim_prox,
    ).exists()
    # Block just ended
    ends = BloqueioUsuario.objects.filter(
        usuario=usuario,
        data_fim__gte=inicio_ant,
        data_fim__lte=fim_ant,
    ).exists()
    return starts or ends


# ─── Scoring Engine ──────────────────────────────────────────────────────────


# ─── Pair Assignment ─────────────────────────────────────────────────────────


def build_stats_cache():
    """Build current workload stats using the single on-call assignment."""
    usuarios = list(UsuarioEscala.objects.filter(ativo=True))
    cache = {
        u.id: {
            'plantoes': u.pl_inicial,
            'oportunidades': u.oportunidades_iniciais,
            'ultima': None,
            'fins_de_semana': 0,
            'feriados_count': 0,
            'feriadoes_count': 0,
        }
        for u in usuarios
    }

    escalas = EscalaDia.objects.filter(
        data__gte=DATA_CORTE_HISTORICO,
        s1__isnull=False,
    ).select_related('s1').order_by('data')
    datas_com_escala = list(escalas.values_list('data', flat=True).distinct())

    for d in datas_com_escala:
        for u in usuarios:
            if _usuario_disponivel(u, d):
                cache[u.id]['oportunidades'] += 1

    for ed in escalas:
        stats = cache.get(ed.s1_id)
        if not stats:
            continue
        stats['plantoes'] += 1
        stats['ultima'] = ed.data
        if ed.fim_de_semana:
            stats['fins_de_semana'] += 1
        if ed.feriado:
            stats['feriados_count'] += 1
        if ed.feriadao:
            stats['feriadoes_count'] += 1

    return cache


def _registrar_oportunidades_do_dia(d, stats_cache):
    """Count this date as an opportunity for every available active manager."""
    for usuario in UsuarioEscala.objects.filter(ativo=True):
        if _usuario_disponivel(usuario, d):
            stats_cache.setdefault(usuario.id, {
                'plantoes': 0,
                'oportunidades': 0,
                'ultima': None,
                'fins_de_semana': 0,
                'feriados_count': 0,
                'feriadoes_count': 0,
            })
            stats_cache[usuario.id]['oportunidades'] += 1


def _registrar_atribuicao(usuario, d, tipo_bloco, stats_cache):
    """Update in-memory workload after assigning a manager."""
    stats = stats_cache.setdefault(usuario.id, {
        'plantoes': 0,
        'oportunidades': 0,
        'ultima': None,
        'fins_de_semana': 0,
        'feriados_count': 0,
        'feriadoes_count': 0,
    })
    stats['plantoes'] += 1
    stats['ultima'] = d
    if tipo_bloco == 'FIM_DE_SEMANA':
        stats['fins_de_semana'] += 1
    elif tipo_bloco == 'FERIADO':
        stats['feriados_count'] += 1
    elif tipo_bloco == 'FERIADAO':
        stats['feriadoes_count'] += 1


def calcular_score_usuario(usuario, data_ref, tipo_bloco, stats_cache):
    """
    Score one manager for a single on-call day. Lower = better candidate.

    Fairness uses assignments divided by available opportunities. Vacation days
    reduce opportunities, so the scheduler does not compensate missed vacation
    days by overloading the manager later.
    """
    stats = stats_cache.get(usuario.id, {
        'plantoes': 0,
        'oportunidades': 0,
        'ultima': None,
        'fins_de_semana': 0,
        'feriados_count': 0,
        'feriadoes_count': 0,
    })

    oportunidades = max(stats.get('oportunidades', 0), 1)
    carga_relativa = stats.get('plantoes', 0) / oportunidades

    score = carga_relativa * 10000
    score += stats.get('plantoes', 0) * 35

    if tipo_bloco == 'FIM_DE_SEMANA':
        score += stats.get('fins_de_semana', 0) * 40
    elif tipo_bloco == 'FERIADO':
        score += stats.get('feriados_count', 0) * 70
    elif tipo_bloco == 'FERIADAO':
        score += stats.get('feriadoes_count', 0) * 70

    ultima = stats.get('ultima')
    if ultima:
        gap_dias = (data_ref - ultima).days
        if gap_dias <= 1:
            score += 100000
        elif gap_dias <= 3:
            score += 600
        elif gap_dias <= 7:
            score += 250
        elif gap_dias <= 14:
            score += 80
    else:
        score -= 100

    return score


def encontrar_melhor_gerente(d, tipo_bloco, stats_cache, atribuicoes_temp=None):
    """Return the best single on-call manager for one date, or None."""
    atribuicoes_temp = atribuicoes_temp or {}
    candidatos = []
    for usuario in UsuarioEscala.objects.filter(ativo=True).select_related('grupo'):
        if not _usuario_disponivel(usuario, d):
            continue
        if _tem_escala_consecutiva(usuario, d, atribuicoes_temp):
            continue
        score = calcular_score_usuario(usuario, d, tipo_bloco, stats_cache)
        candidatos.append((score, usuario.nome, usuario.id, usuario))

    if not candidatos:
        return None

    candidatos.sort(key=lambda item: (item[0], item[1], item[2]))
    return candidatos[0][3]


def encontrar_melhor_par(bloco, stats_cache):
    """
    Compatibility wrapper: returns daily single-manager assignments in s1.
    s2 is always empty under the current scheduling rule.
    """
    assignments = {}
    temp_assignments = {}
    local_stats = {
        user_id: stats.copy()
        for user_id, stats in stats_cache.items()
    }

    for d in sorted(bloco['days']):
        _registrar_oportunidades_do_dia(d, local_stats)
        gerente = encontrar_melhor_gerente(d, bloco['type'], local_stats, temp_assignments)
        if not gerente:
            return None
        assignments[d] = {'s1': gerente, 's2': None}
        temp_assignments[d] = gerente
        _registrar_atribuicao(gerente, d, bloco['type'], local_stats)

    return {'s1': None, 's2': None, '_assignments': assignments}


# ─── Scale Generation ────────────────────────────────────────────────────────

def gerar_escala_mensal(
    ano, mes, preservar_manuais=True, usuario_log=None, forcar=False,
    data_minima=None,
):
    """
    Generate/regenerate on-call schedule for a full month.

    Args:
        ano, mes: target month
        preservar_manuais: keep manual edits
        usuario_log: Django user for audit trail
        forcar: if True, bypass month lock check (admin only)

    Returns: (created_count, updated_count, errors)
    """
    # Guard: refuse to modify locked months unless forced
    if is_mes_fechado(ano, mes) and not forcar:
        AlertaSistema.objects.create(
            tipo='MES_FECHADO',
            data_referencia=date(ano, mes, 1),
            descricao=f'Tentativa de regenerar mês fechado: {mes:02d}/{ano}. Operação bloqueada.'
        )
        return 0, [f'Mês {mes:02d}/{ano} está fechado e não pode ser alterado.']

    primeiro_dia_mes = date(ano, mes, 1)
    if data_minima and data_minima.year == ano and data_minima.month == mes:
        inicio_regeneracao = data_minima
    else:
        inicio_regeneracao = primeiro_dia_mes

    blocos = get_blocos_cobertura(ano, mes)

    # Collect manual assignments to preserve
    manuais = {}
    if preservar_manuais:
        for ed in EscalaDia.objects.filter(
            data__year=ano, data__month=mes, manual=True
        ):
            manuais[ed.data] = ed

    # Remove only assignments inside the regeneration window.
    # Earlier days in the same month are part of the already published rota.
    EscalaDia.objects.filter(
        data__year=ano, data__month=mes, data__gte=inicio_regeneracao,
        status='AUTOMATICA',
    ).delete()

    stats_cache = build_stats_cache()

    criados = 0
    erros = []

    for bloco in blocos:
        # Skip days before the requested regeneration window or already covered manually.
        uncovered = [d for d in bloco['days'] if d >= inicio_regeneracao and d not in manuais]
        if not uncovered:
            continue

        # For partial coverage, split into sub-blocks
        if len(uncovered) < len(bloco['days']):
            sub_runs = []
            cur = []
            for d in sorted(uncovered):
                if not cur or (d - cur[-1]).days == 1:
                    cur.append(d)
                else:
                    sub_runs.append(cur)
                    cur = [d]
            if cur:
                sub_runs.append(cur)

            for sr in sub_runs:
                mini_bloco = {**bloco, 'days': sr}
                pair = encontrar_melhor_par(mini_bloco, stats_cache)
                if pair:
                    for d, assign in pair['_assignments'].items():
                        if d in manuais:
                            continue
                        EscalaDia.objects.update_or_create(
                            data=d,
                            defaults={
                                's1': assign['s1'],
                                's2': assign['s2'],
                                'fim_de_semana': bloco['type'] == 'FIM_DE_SEMANA',
                                'feriado': bloco['type'] == 'FERIADO',
                                'feriadao': bloco['type'] == 'FERIADAO',
                                'dia_util': False,
                                'manual': False,
                                'status': 'AUTOMATICA',
                            }
                        )
                        criados += 1
                        _registrar_oportunidades_do_dia(d, stats_cache)
                        if assign['s1']:
                            _registrar_atribuicao(assign['s1'], d, bloco['type'], stats_cache)

                else:
                    erros.append(f'Sem gerente disponível para {bloco["nome"]} ({sr[0]} a {sr[-1]})')
            continue

        # Full block uncovered
        pair = encontrar_melhor_par(bloco, stats_cache)
        if pair:
            for d, assign in pair['_assignments'].items():
                EscalaDia.objects.update_or_create(
                    data=d,
                    defaults={
                        's1': assign['s1'],
                        's2': assign['s2'],
                        'fim_de_semana': bloco['type'] == 'FIM_DE_SEMANA',
                        'feriado': bloco['type'] == 'FERIADO',
                        'feriadao': bloco['type'] == 'FERIADAO',
                        'dia_util': False,
                        'manual': False,
                        'status': 'AUTOMATICA',
                    }
                )
                criados += 1
                _registrar_oportunidades_do_dia(d, stats_cache)
                if assign['s1']:
                    _registrar_atribuicao(assign['s1'], d, bloco['type'], stats_cache)

        else:
            erros.append(f'Sem gerente disponível para {bloco["nome"]} ({bloco["days"][0]} a {bloco["days"][-1]})')

    # Update user counters
    _atualizar_contadores_usuarios()

    # Save EscalaBloco records
    EscalaBloco.objects.filter(data_inicio__year=ano, data_inicio__month=mes).delete()
    for bloco in blocos:
        EscalaBloco.objects.create(
            tipo=bloco['type'],
            data_inicio=bloco['days'][0],
            data_fim=bloco['days'][-1],
            nome=bloco['nome'],
        )

    return criados, erros


def gerar_escala_anual(ano, preservar_manuais=True, usuario_log=None, forcar=False):
    """Generate scale for an entire year. Skips locked months unless forced."""
    total_criados = 0
    total_erros = []
    for mes in range(1, 13):
        criados, erros = gerar_escala_mensal(ano, mes, preservar_manuais, usuario_log, forcar)
        total_criados += criados
        if erros:
            total_erros.extend(erros)
    return total_criados, total_erros


def gerar_escala_periodo(data_inicio, data_fim, preservar_manuais=True, usuario_log=None):
    """
    Generate scale for a date range (inclusive).
    Skips locked months. Returns (total_criados, total_erros, meses_pulados).
    """
    cursor = date(data_inicio.year, data_inicio.month, 1)
    fim = date(data_fim.year, data_fim.month, 1)

    total_criados = 0
    total_erros = []
    meses_pulados = []

    while cursor <= fim:
        if is_mes_fechado(cursor.year, cursor.month):
            meses_pulados.append(f'{cursor.month:02d}/{cursor.year}')
        else:
            c, e = gerar_escala_mensal(cursor.year, cursor.month, preservar_manuais, usuario_log)
            total_criados += c
            if e:
                total_erros.extend(e)

        # Next month
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    return total_criados, total_erros, meses_pulados


def regenerar_apos_data(data_inicio, usuario_log=None):
    """
    Regenerate scale from a given date forward. Skips locked months.
    Used after adding/removing blocks.
    """
    mes_atual = data_inicio.month
    ano_atual = data_inicio.year
    criados = 0
    erros = []
    meses_pulados = []

    # Regenerate current month from data_inicio, then the next 5 full months.
    for indice_mes in range(6):
        if is_mes_fechado(ano_atual, mes_atual):
            meses_pulados.append(f'{mes_atual:02d}/{ano_atual}')
        else:
            data_minima = data_inicio if indice_mes == 0 else None
            c, e = gerar_escala_mensal(
                ano_atual, mes_atual, True, usuario_log, data_minima=data_minima
            )
            criados += c
            if e:
                erros.extend(e)

        mes_atual += 1
        if mes_atual > 12:
            mes_atual = 1
            ano_atual += 1

    if meses_pulados:
        AlertaSistema.objects.create(
            tipo='MES_FECHADO',
            data_referencia=data_inicio,
            descricao=f'Meses fechados pulados na regeneração a partir de {data_inicio}: {", ".join(meses_pulados)}.'
        )

    return criados, erros


# ─── Impact Analysis ────────────────────────────────────────────────────────

def analisar_impacto_ferias(bloqueio):
    """
    Analyze the impact of a vacation block on the scale.

    Returns a dict with:
    - dias_afetados: number of scale days the user would have been assigned
    - usuarios_impactados: users who will take over the assignments
    - blocos_afetados: coverage blocks affected
    - alertas: list of warnings
    """
    usuario = bloqueio.usuario
    inicio = bloqueio.data_inicio
    fim = bloqueio.data_fim

    # Find scale days where this user is on call in the period
    dias_afetados = EscalaDia.objects.filter(
        data__gte=inicio, data__lte=fim, s1=usuario
    )

    # Count single-role assignments
    s1_afetados = dias_afetados.filter(s1=usuario).count()
    s2_afetados = 0

    # Find coverage blocks in the period
    blocos_afetados = EscalaBloco.objects.filter(
        data_inicio__lte=fim, data_fim__gte=inicio
    )

    # Check for locked months in the period
    cursor = date(inicio.year, inicio.month, 1)
    fim_mes = date(fim.year, fim.month, 1)
    meses_fechados = []
    while cursor <= fim_mes:
        if is_mes_fechado(cursor.year, cursor.month):
            meses_fechados.append(f'{cursor.month:02d}/{cursor.year}')
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)

    alertas = []
    if meses_fechados:
        alertas.append(f'Meses fechados no período: {", ".join(meses_fechados)}. Não serão alterados.')
    if s1_afetados + s2_afetados == 0:
        alertas.append('Nenhuma escala afetada — usuário não estava escalado neste período.')
    else:
        alertas.append(f'{s1_afetados + s2_afetados} dias de escala precisarão ser redistribuídos.')

    disponiveis = UsuarioEscala.objects.filter(ativo=True).exclude(id=usuario.id).count()
    if disponiveis == 0:
        alertas.append('Nenhum outro gerente ativo disponível para cobrir o período.')

    return {
        'usuario': usuario.nome,
        'periodo': f'{inicio} a {fim}',
        'dias_afetados': s1_afetados + s2_afetados,
        's1_afetados': s1_afetados,
        's2_afetados': s2_afetados,
        'blocos_afetados': blocos_afetados.count(),
        'meses_fechados': meses_fechados,
        'disponiveis': disponiveis,
        'disponiveis_grupo_a': disponiveis,
        'disponiveis_grupo_b': 0,
        'alertas': alertas,
    }


# ─── Counter Update ──────────────────────────────────────────────────────────

def _atualizar_contadores_usuarios():
    """Recalculate user counters using the single on-call assignment."""
    for u in UsuarioEscala.objects.filter(ativo=True):
        escalas_contabilizadas = EscalaDia.objects.filter(
            s1=u,
            data__gte=DATA_CORTE_HISTORICO,
        )
        u.total_s1 = u.pl_inicial + escalas_contabilizadas.count()
        u.total_s2 = 0
        u.total_dias_trabalhados = 0
        u.total_dias_sobreaviso = u.total_s1
        u.total_feriados = escalas_contabilizadas.filter(feriado=True).count()
        u.total_feriadoes = escalas_contabilizadas.filter(feriadao=True).count()
        u.feriadao_s1_count = u.total_feriadoes
        u.feriadao_s2_count = 0
        ultima = EscalaDia.objects.filter(s1=u).order_by('-data').first()
        u.ultima_escala = ultima.data if ultima else None
        u.save(update_fields=[
            'total_s1', 'total_s2', 'total_dias_trabalhados',
            'total_dias_sobreaviso', 'total_feriados', 'total_feriadoes',
            'feriadao_s1_count', 'feriadao_s2_count', 'ultima_escala',
        ])


# ─── Conflict Detection ──────────────────────────────────────────────────────

def validar_dia(data, s1, s2):
    """Validate a day assignment. Returns list of warnings/errors."""
    problemas = []

    usuario = s1
    if not usuario:
        return problemas

    bloqueado = BloqueioUsuario.objects.filter(
        usuario=usuario, data_inicio__lte=data, data_fim__gte=data
    ).first()
    if bloqueado:
        problemas.append({
            'tipo': 'erro',
            'msg': f'{usuario.nome} está indisponível: {bloqueado.get_tipo_display()} até {bloqueado.data_fim}.'
        })

    for adj in (data - timedelta(days=1), data + timedelta(days=1)):
        escala_adj = EscalaDia.objects.filter(data=adj, s1=usuario).first()
        if escala_adj:
            problemas.append({
                'tipo': 'erro',
                'msg': f'{usuario.nome} já está em sobreaviso em {adj}. Não é permitido repetir dois dias seguidos.'
            })

    return problemas


# ─── Reports ─────────────────────────────────────────────────────────────────

def get_relatorio_usuarios(ano=None, mes=None):
    """
    Build per-user report with all counters.
    Returns list of dicts.
    """
    usuarios = UsuarioEscala.objects.filter(ativo=True).select_related('grupo')
    filtro = dm.Q()
    if ano:
        filtro &= dm.Q(data__year=ano)
    if mes:
        filtro &= dm.Q(data__month=mes)
    inclui_historico = (not mes) and (ano is None or ano == DATA_CORTE_HISTORICO.year)
    if inclui_historico:
        filtro &= dm.Q(data__gte=DATA_CORTE_HISTORICO)

    relatorio = []
    for u in usuarios:
        escalas = EscalaDia.objects.filter(filtro, s1=u)
        s1_count = escalas.filter(s1=u).count()
        if inclui_historico:
            s1_count += u.pl_inicial
        s2_count = 0
        ferias_dias = 0
        for blk in BloqueioUsuario.objects.filter(usuario=u, tipo='FERIAS'):
            ferias_dias += (blk.data_fim - blk.data_inicio).days + 1

        relatorio.append({
            'usuario': u,
            'grupo': u.grupo.nome,
            'pl_total': s1_count,
            's1': s1_count,
            's2': u.total_s2,
            'ferias_dias': ferias_dias,
            'feriadao_s1': escalas.filter(feriadao=True).count(),
            'feriadao_s2': 0,
            'ultima_escala': u.ultima_escala,
        })

    return relatorio


def get_alertas_desequilibrio():
    """Detect relevant workload issues under the single on-call rule."""
    alertas = []
    usuarios = list(UsuarioEscala.objects.filter(ativo=True).select_related('grupo'))
    if not usuarios:
        return alertas

    stats = build_stats_cache()
    cargas = []
    for u in usuarios:
        s = stats.get(u.id, {})
        oportunidades = s.get('oportunidades', 0)
        plantoes = s.get('plantoes', 0)
        if oportunidades:
            cargas.append((u, plantoes, oportunidades, plantoes / oportunidades))

        escalas = EscalaDia.objects.filter(
            s1=u,
            data__gte=DATA_CORTE_HISTORICO,
        ).order_by('data')
        prev_data = None
        for ed in escalas:
            if prev_data and (ed.data - prev_data).days == 1:
                alertas.append(
                    f'{u.nome} está escalado em dias consecutivos ({prev_data} e {ed.data}).'
                )
                break
            prev_data = ed.data

    if len(cargas) >= 2:
        cargas.sort(key=lambda item: item[3])
        menor = cargas[0]
        maior = cargas[-1]
        if maior[3] - menor[3] > 0.25 and maior[1] - menor[1] > 2:
            alertas.append(
                f'Desequilíbrio de sobreaviso: {maior[0].nome} tem {maior[1]} plantões '
                f'em {maior[2]} dias disponíveis, enquanto {menor[0].nome} tem '
                f'{menor[1]} em {menor[2]}. Férias reduzem os dias disponíveis e não '
                f'são compensadas como dívida.'
            )

    return alertas


# ─── Summary Tables ──────────────────────────────────────────────────────────

def _count_user_days_in_range(usuario, inicio, fim):
    """
    Count a user's stats in a date range.
    Returns dict with all breakdown columns for the summary table.
    """
    inclui_historico = inicio <= HISTORICO_INICIO and fim >= HISTORICO_FIM
    data_inicio_escalas = max(inicio, DATA_CORTE_HISTORICO) if inclui_historico else inicio

    escalas = EscalaDia.objects.filter(
        data__gte=data_inicio_escalas, data__lte=fim, s1=usuario
    )

    total_s1 = escalas.filter(s1=usuario).count()
    if inclui_historico:
        total_s1 += usuario.pl_inicial
    total_s2 = 0

    # By day type
    sabados = escalas.filter(
        fim_de_semana=True, data__week_day=7  # Django: 7=Saturday
    ).count()
    domingos = escalas.filter(
        fim_de_semana=True, data__week_day=1  # Django: 1=Sunday
    ).count()
    feriados = escalas.filter(feriado=True).count()
    feriadoes_count = escalas.filter(feriadao=True).count()

    # Count block days within range (Python — simple and correct)
    ferias_dias = 0
    bloqueios_dias = 0
    for blk in BloqueioUsuario.objects.filter(
        usuario=usuario,
        data_inicio__lte=fim, data_fim__gte=inicio,
    ):
        overlap_inicio = max(blk.data_inicio, inicio)
        overlap_fim = min(blk.data_fim, fim)
        dias = (overlap_fim - overlap_inicio).days + 1
        if blk.tipo == 'FERIAS':
            ferias_dias += dias
        else:
            bloqueios_dias += dias

    dias_cobertura = list(
        EscalaDia.objects.filter(
            data__gte=data_inicio_escalas, data__lte=fim, s1__isnull=False
        ).values_list('data', flat=True).distinct()
    )
    dias_disponiveis = sum(1 for d in dias_cobertura if _usuario_disponivel(usuario, d))
    if inclui_historico:
        dias_disponiveis += usuario.oportunidades_iniciais

    return {
        'usuario': usuario,
        'grupo': usuario.grupo.nome,
        'total_plantoes': total_s1,
        'dias_disponiveis': dias_disponiveis,
        'percentual_carga': (total_s1 / dias_disponiveis * 100) if dias_disponiveis else 0,
        'sabados': sabados,
        'domingos': domingos,
        'feriados': feriados,
        'feriadoes': feriadoes_count,
        'ferias_dias': int(ferias_dias),
        'bloqueios_dias': int(bloqueios_dias),
        's1': total_s1,
        's2': total_s2,
    }


def calcular_resumo_mensal(ano, mes):
    """Return summary table data for a specific month. Ordered by group then total plantoes desc."""
    import calendar
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    inicio = date(ano, mes, 1)
    fim = date(ano, mes, ultimo_dia)

    dados = []
    for u in UsuarioEscala.objects.all().select_related('grupo').order_by('grupo__nome', 'nome'):
        dados.append(_count_user_days_in_range(u, inicio, fim))

    # Sort: group A first, then by total_plantoes desc
    dados.sort(key=lambda x: (x['grupo'], -x['total_plantoes']))
    return dados


def calcular_resumo_anual(ano):
    """Return summary table data for an entire year."""
    inicio = date(ano, 1, 1)
    fim = date(ano, 12, 31)

    dados = []
    for u in UsuarioEscala.objects.all().select_related('grupo').order_by('grupo__nome', 'nome'):
        dados.append(_count_user_days_in_range(u, inicio, fim))

    dados.sort(key=lambda x: (x['grupo'], -x['total_plantoes']))
    return dados
