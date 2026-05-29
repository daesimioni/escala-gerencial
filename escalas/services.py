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


def get_dias_desde_ultima_escala(usuario, data_ref):
    """Days since user's last assignment."""
    ultima = EscalaDia.objects.filter(
        dm.Q(s1=usuario) | dm.Q(s2=usuario),
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

def calcular_score_usuario(usuario, role, bloco, stats_cache):
    """
    Score a user for a given role in a block. Lower = better candidate.

    Factors (all lower = better candidate):
    - Total plantões (weight: 100)
    - Role-specific count: S1/S2 (weight: 50)
    - Recency (weight: up to 500 for very recent)
    - Fins de semana (weight: 80)
    - Feriados (weight: 120)
    - Feriadão rotation (weight: 300)
    - Block proximity penalty (weight: 1000)
    - Just returned from vacation bonus (weight: -150)
    - About to enter vacation (weight: 800)
    """
    stats = stats_cache.get(usuario.id, {
        'plantoes': usuario.pl_inicial,
        's1': usuario.total_s1,
        's2': usuario.total_s2,
        'feriadao_s1': usuario.feriadao_s1_count,
        'feriadao_s2': usuario.feriadao_s2_count,
        'ultima': None,
        'fins_de_semana': 0,
        'feriados_count': 0,
    })

    score = 0.0

    # Base: total plantões (combine initial + computed)
    score += stats['plantoes'] * 100

    # Role balance
    if role == 'S1':
        score += stats['s1'] * 50
    else:
        score += stats['s2'] * 50

    # Fins de semana trabalhados
    score += stats['fins_de_semana'] * 80

    # Feriados pegos
    if bloco['type'] == 'FERIADO':
        score += stats['feriados_count'] * 120

    # Recency
    if stats['ultima']:
        gap_dias = (bloco['days'][0] - stats['ultima']).days
        if gap_dias < 7:
            score += 500
        elif gap_dias < 10:
            score += 250
        elif gap_dias < 14:
            score += 100
        elif gap_dias < 21:
            score += 30
    else:
        score -= 200  # Bonus for never assigned

    # Feriadão rotation
    if bloco['type'] == 'FERIADAO':
        if role == 'S1':
            score += stats['feriadao_s1'] * 300
        else:
            score += stats['feriadao_s2'] * 300

    # Historical FER: users with more historical vacation days should get
    # slightly more assignments going forward (they've rested more).
    # Negative score = preference. Capped at reasonable impact.
    score -= min(usuario.fer_inicial, 30) * 15

    # Just returned from vacation — don't overload immediately (negative = bonus/priority)
    if _voltou_de_ferias_recentemente(usuario, bloco['days'][0]):
        score -= 150

    # About to enter vacation — heavy penalty to avoid scheduling
    if _vai_entrar_de_ferias(usuario, bloco['days'][0]):
        score += 800

    # Block proximity check
    if get_bloqueios_proximos(usuario, bloco['days'][0]):
        score += 1000

    return score


def _voltou_de_ferias_recentemente(usuario, data_ref, dias=3):
    """Check if user just returned from vacation (within `dias` days)."""
    fim_ferias = data_ref - timedelta(days=dias)
    return BloqueioUsuario.objects.filter(
        usuario=usuario, tipo='FERIAS',
        data_fim__gte=fim_ferias,
        data_fim__lt=data_ref,
    ).exists()


def _vai_entrar_de_ferias(usuario, data_ref, dias=5):
    """Check if user is about to go on vacation (within `dias` days)."""
    inicio_ferias = data_ref + timedelta(days=dias)
    return BloqueioUsuario.objects.filter(
        usuario=usuario, tipo='FERIAS',
        data_inicio__gt=data_ref,
        data_inicio__lte=inicio_ferias,
    ).exists()


def build_stats_cache():
    """Build a stats dict for all users from current DB state."""
    cache = {}
    for u in UsuarioEscala.objects.filter(ativo=True):
        # Count assignments from EscalaDia
        all_escalas = EscalaDia.objects.filter(dm.Q(s1=u) | dm.Q(s2=u))
        s1_count = all_escalas.filter(s1=u).count()
        s2_count = all_escalas.filter(s2=u).count()
        fds_count = all_escalas.filter(fim_de_semana=True).count()
        feriados_count = all_escalas.filter(feriado=True).count()
        ultima = all_escalas.order_by('-data').first()

        cache[u.id] = {
            'plantoes': u.pl_inicial + s1_count + s2_count,
            's1': u.total_s1 + s1_count,
            's2': u.total_s2 + s2_count,
            'feriadao_s1': u.feriadao_s1_count,
            'feriadao_s2': u.feriadao_s2_count,
            'fins_de_semana': fds_count,
            'feriados_count': feriados_count,
            'ultima': ultima.data if ultima else None,
        }
    return cache


# ─── Pair Assignment ─────────────────────────────────────────────────────────

def encontrar_melhor_par(bloco, stats_cache):
    """
    Find best S1/S2 pair for a coverage block.

    Returns: {s1: UsuarioEscala, s2: UsuarioEscala, _assignments: {date: {s1, s2}}}
    or None if no valid pair.
    """
    grupo_a = GrupoEscala.objects.get(nome='A')
    grupo_b = GrupoEscala.objects.get(nome='B')

    disponiveis_a = get_usuarios_disponiveis(bloco['days'][0], grupo_a)
    disponiveis_b = get_usuarios_disponiveis(bloco['days'][0], grupo_b)

    if not disponiveis_a or not disponiveis_b:
        return None

    best_pair = None
    best_score = float('inf')

    for ua in disponiveis_a:
        for ub in disponiveis_b:
            # ua=S1, ub=S2
            s1_score = calcular_score_usuario(ua, 'S1', bloco, stats_cache)
            s2_score = calcular_score_usuario(ub, 'S2', bloco, stats_cache)
            total = s1_score + s2_score
            if total < best_score:
                best_score = total
                best_pair = {'s1': ua, 's2': ub}

            # ua=S2, ub=S1
            s1_score = calcular_score_usuario(ub, 'S1', bloco, stats_cache)
            s2_score = calcular_score_usuario(ua, 'S2', bloco, stats_cache)
            total = s1_score + s2_score
            if total < best_score:
                best_score = total
                best_pair = {'s1': ub, 's2': ua}

    if not best_pair:
        return None

    # Create per-day assignments based on block type
    days = sorted(bloco['days'])
    assignments = {}

    if bloco['type'] == 'FERIADAO':
        if len(days) == 1:
            assignments[days[0]] = {'s1': best_pair['s1'], 's2': best_pair['s2']}
        elif len(days) == 2:
            assignments[days[0]] = {'s1': best_pair['s1'], 's2': best_pair['s2']}
            assignments[days[1]] = {'s1': best_pair['s2'], 's2': best_pair['s1']}
        elif len(days) == 3:
            assignments[days[0]] = {'s1': best_pair['s1'], 's2': best_pair['s2']}
            assignments[days[1]] = {'s1': best_pair['s1'], 's2': best_pair['s2']}
            assignments[days[2]] = {'s1': best_pair['s2'], 's2': best_pair['s1']}
        else:
            assignments[days[0]] = {'s1': best_pair['s1'], 's2': best_pair['s2']}
            assignments[days[1]] = {'s1': best_pair['s1'], 's2': best_pair['s2']}
            for i in range(2, len(days) - 1):
                if i % 2 == 0:
                    assignments[days[i]] = {'s1': best_pair['s1'], 's2': best_pair['s2']}
                else:
                    assignments[days[i]] = {'s1': best_pair['s2'], 's2': best_pair['s1']}
            assignments[days[-1]] = {'s1': best_pair['s2'], 's2': best_pair['s1']}
    else:
        # Regular block: alternate S1/S2 for multi-day blocks
        for i, d in enumerate(days):
            if i % 2 == 0:
                assignments[d] = {'s1': best_pair['s1'], 's2': best_pair['s2']}
            else:
                assignments[d] = {'s1': best_pair['s2'], 's2': best_pair['s1']}

    best_pair['_assignments'] = assignments
    return best_pair


# ─── Scale Generation ────────────────────────────────────────────────────────

def gerar_escala_mensal(ano, mes, preservar_manuais=True, usuario_log=None, forcar=False):
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

    blocos = get_blocos_cobertura(ano, mes)
    stats_cache = build_stats_cache()

    # Collect manual assignments to preserve
    manuais = {}
    if preservar_manuais:
        for ed in EscalaDia.objects.filter(
            data__year=ano, data__month=mes, manual=True
        ):
            manuais[ed.data] = ed

    # Remove existing automatic assignments for the month (preserve MANUAL, CONFIRMADA, FECHADA, BLOQUEADA)
    EscalaDia.objects.filter(
        data__year=ano, data__month=mes, status='AUTOMATICA'
    ).delete()

    criados = 0
    erros = []

    for bloco in blocos:
        # Skip days already covered by manual assignments
        uncovered = [d for d in bloco['days'] if d not in manuais]
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
                        if assign['s1']:
                            stats_cache.setdefault(assign['s1'].id, {})['plantoes'] = stats_cache.get(assign['s1'].id, {}).get('plantoes', 0) + 1
                            stats_cache.setdefault(assign['s1'].id, {})['s1'] = stats_cache.get(assign['s1'].id, {}).get('s1', 0) + 1
                        if assign['s2']:
                            stats_cache.setdefault(assign['s2'].id, {})['plantoes'] = stats_cache.get(assign['s2'].id, {}).get('plantoes', 0) + 1
                            stats_cache.setdefault(assign['s2'].id, {})['s2'] = stats_cache.get(assign['s2'].id, {}).get('s2', 0) + 1

                        if bloco['type'] == 'FERIADAO':
                            if assign['s1']:
                                assign['s1'].feriadao_s1_count += 1
                                assign['s1'].save(update_fields=['feriadao_s1_count'])
                            if assign['s2']:
                                assign['s2'].feriadao_s2_count += 1
                                assign['s2'].save(update_fields=['feriadao_s2_count'])
                else:
                    erros.append(f'Sem par disponível para bloco {bloco["nome"]} ({sr[0]} a {sr[-1]})')
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
                if assign['s1']:
                    stats_cache.setdefault(assign['s1'].id, {})['plantoes'] = stats_cache.get(assign['s1'].id, {}).get('plantoes', 0) + 1
                    stats_cache.setdefault(assign['s1'].id, {})['s1'] = stats_cache.get(assign['s1'].id, {}).get('s1', 0) + 1
                if assign['s2']:
                    stats_cache.setdefault(assign['s2'].id, {})['plantoes'] = stats_cache.get(assign['s2'].id, {}).get('plantoes', 0) + 1
                    stats_cache.setdefault(assign['s2'].id, {})['s2'] = stats_cache.get(assign['s2'].id, {}).get('s2', 0) + 1

                if bloco['type'] == 'FERIADAO':
                    if assign['s1']:
                        assign['s1'].feriadao_s1_count += 1
                        assign['s1'].save(update_fields=['feriadao_s1_count'])
                    if assign['s2']:
                        assign['s2'].feriadao_s2_count += 1
                        assign['s2'].save(update_fields=['feriadao_s2_count'])
        else:
            erros.append(f'Sem par disponível para bloco {bloco["nome"]} ({bloco["days"][0]} a {bloco["days"][-1]})')

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

    # Regenerate current month + next 5 months, skipping locked ones
    for _ in range(6):
        if is_mes_fechado(ano_atual, mes_atual):
            meses_pulados.append(f'{mes_atual:02d}/{ano_atual}')
        else:
            c, e = gerar_escala_mensal(ano_atual, mes_atual, True, usuario_log)
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

    # Find scale days where this user is S1 or S2 in the period
    dias_afetados = EscalaDia.objects.filter(
        data__gte=inicio, data__lte=fim
    ).filter(dm.Q(s1=usuario) | dm.Q(s2=usuario))

    # Count by role
    s1_afetados = dias_afetados.filter(s1=usuario).count()
    s2_afetados = dias_afetados.filter(s2=usuario).count()

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

    # Get available users who can cover
    disponiveis_a = UsuarioEscala.objects.filter(ativo=True, grupo__nome='A').exclude(id=usuario.id).count()
    disponiveis_b = UsuarioEscala.objects.filter(ativo=True, grupo__nome='B').exclude(id=usuario.id).count()
    if disponiveis_a == 0:
        alertas.append('⚠️ Nenhum usuário disponível no Grupo A para cobrir o período!')
    if disponiveis_b == 0:
        alertas.append('⚠️ Nenhum usuário disponível no Grupo B para cobrir o período!')

    return {
        'usuario': usuario.nome,
        'periodo': f'{inicio} a {fim}',
        'dias_afetados': s1_afetados + s2_afetados,
        's1_afetados': s1_afetados,
        's2_afetados': s2_afetados,
        'blocos_afetados': blocos_afetados.count(),
        'meses_fechados': meses_fechados,
        'disponiveis_grupo_a': disponiveis_a,
        'disponiveis_grupo_b': disponiveis_b,
        'alertas': alertas,
    }


# ─── Counter Update ──────────────────────────────────────────────────────────

def _atualizar_contadores_usuarios():
    """Recalculate user PL, S1, S2 counters from EscalaDia."""
    for u in UsuarioEscala.objects.filter(ativo=True):
        u.total_s1 = EscalaDia.objects.filter(s1=u).count()
        u.total_s2 = EscalaDia.objects.filter(s2=u).count()
        u.total_dias_trabalhados = u.total_s1
        u.total_dias_sobreaviso = u.total_s2
        u.total_feriados = EscalaDia.objects.filter(
            dm.Q(s1=u) | dm.Q(s2=u), feriado=True
        ).count()
        u.total_feriadoes = EscalaDia.objects.filter(
            dm.Q(s1=u) | dm.Q(s2=u), feriadao=True
        ).count()
        ultima = EscalaDia.objects.filter(
            dm.Q(s1=u) | dm.Q(s2=u)
        ).order_by('-data').first()
        u.ultima_escala = ultima.data if ultima else None
        u.save(update_fields=[
            'total_s1', 'total_s2', 'total_dias_trabalhados',
            'total_dias_sobreaviso', 'total_feriados', 'total_feriadoes',
            'ultima_escala',
        ])


# ─── Conflict Detection ──────────────────────────────────────────────────────

def validar_dia(data, s1, s2):
    """Validate a day assignment. Returns list of warnings/errors."""
    problemas = []

    if s1 and s2 and s1.grupo_id == s2.grupo_id:
        problemas.append({
            'tipo': 'erro',
            'msg': f'Dupla inválida: {s1.nome} e {s2.nome} são do mesmo grupo.'
        })

    for usuario, role in [(s1, 'S1'), (s2, 'S2')]:
        if not usuario:
            continue
        bloqueado = BloqueioUsuario.objects.filter(
            usuario=usuario, data_inicio__lte=data, data_fim__gte=data
        ).first()
        if bloqueado:
            problemas.append({
                'tipo': 'erro',
                'msg': f'{usuario.nome} ({role}) está bloqueado: {bloqueado.get_tipo_display()} até {bloqueado.data_fim}.'
            })

        # Check proximity to blocks
        margem = 3
        prox_inicio = BloqueioUsuario.objects.filter(
            usuario=usuario,
            data_inicio__gte=data,
            data_inicio__lte=data + timedelta(days=margem),
        ).first()
        if prox_inicio:
            problemas.append({
                'tipo': 'alerta',
                'msg': f'{usuario.nome} ({role}) tem {prox_inicio.get_tipo_display()} começando em {prox_inicio.data_inicio}.'
            })

        prox_fim = BloqueioUsuario.objects.filter(
            usuario=usuario,
            data_fim__gte=data - timedelta(days=margem),
            data_fim__lte=data,
        ).first()
        if prox_fim:
            problemas.append({
                'tipo': 'alerta',
                'msg': f'{usuario.nome} ({role}) teve {prox_fim.get_tipo_display()} terminando em {prox_fim.data_fim}.'
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

    relatorio = []
    for u in usuarios:
        escalas = EscalaDia.objects.filter(filtro).filter(dm.Q(s1=u) | dm.Q(s2=u))
        s1_count = escalas.filter(s1=u).count()
        s2_count = escalas.filter(s2=u).count()
        ferias_dias = BloqueioUsuario.objects.filter(
            usuario=u, tipo='FERIAS',
        ).aggregate(
            total=dm.Sum(dm.F('data_fim') - dm.F('data_inicio') + 1)
        )['total'] or 0

        relatorio.append({
            'usuario': u,
            'grupo': u.grupo.nome,
            'pl_total': u.pl_inicial + s1_count + s2_count,
            's1': u.total_s1,
            's2': u.total_s2,
            'ferias_dias': ferias_dias,
            'feriadao_s1': u.feriadao_s1_count,
            'feriadao_s2': u.feriadao_s2_count,
            'ultima_escala': u.ultima_escala,
        })

    return relatorio


def get_alertas_desequilibrio():
    """
    Detect workload imbalance and explain the cause.
    All alerts include the reason so users understand whether it's
    structural (group size difference), by design (feriadão block),
    or something that needs attention.
    """
    alertas = []

    for grupo in GrupoEscala.objects.all():
        usuarios = list(UsuarioEscala.objects.filter(ativo=True, grupo=grupo))
        if len(usuarios) < 2:
            continue

        # PL comparison within group
        plantoes = []
        for u in usuarios:
            gen = EscalaDia.objects.filter(dm.Q(s1=u) | dm.Q(s2=u)).count()
            plantoes.append((u, u.pl_inicial + gen))

        plantoes.sort(key=lambda x: x[1])
        menor = plantoes[0]
        maior = plantoes[-1]
        diff = maior[1] - menor[1]

        if diff > 4:
            alertas.append(
                f'Grupo {grupo.nome}: {maior[0].nome} tem {diff} plantoes a mais '
                f'que {menor[0].nome}. Causa: diferença no PL inicial da planilha '
                f'({maior[0].nome} PL={maior[0].pl_inicial} vs {menor[0].nome} PL={menor[0].pl_inicial}). '
                f'O algoritmo está redistribuindo gradualmente.'
            )

        # Consecutive days — show both feriadão and regular
        for u in usuarios:
            escalas = EscalaDia.objects.filter(
                dm.Q(s1=u) | dm.Q(s2=u)
            ).order_by('data')

            consecutivas = 0
            max_consec = 0
            max_consec_info = ''
            prev_data = None

            for ed in escalas:
                if prev_data and (ed.data - prev_data).days == 1:
                    consecutivas += 1
                    if consecutivas > max_consec:
                        max_consec = consecutivas
                        max_consec_info = 'feriadão' if ed.feriadao else 'fins de semana seguidos'
                else:
                    consecutivas = 1
                prev_data = ed.data

            if max_consec >= 4:
                alertas.append(
                    f'{u.nome} tem {max_consec} dias consecutivos com escala '
                    f'({max_consec_info}). '
                    f'{"Isso é esperado — regra do feriadão." if "feriadão" in max_consec_info else "Verificar se há alternativa."}'
                )

    # Cross-group explanation
    ga = UsuarioEscala.objects.filter(ativo=True, grupo__nome='A').count()
    gb = UsuarioEscala.objects.filter(ativo=True, grupo__nome='B').count()
    if ga != gb:
        alertas.append(
            f'Grupo A: {ga} pessoas, Grupo B: {gb} pessoas. '
            f'Toda escala exige 1A+1B, então cada pessoa do Grupo B '
            f'naturalmente pega ~{round((ga/gb - 1) * 100)}% mais plantões. '
            f'Isso é estrutural, não um erro de distribuição.'
        )

    return alertas


# ─── Summary Tables ──────────────────────────────────────────────────────────

def _count_user_days_in_range(usuario, inicio, fim):
    """
    Count a user's stats in a date range.
    Returns dict with all breakdown columns for the summary table.
    """
    escalas = EscalaDia.objects.filter(
        data__gte=inicio, data__lte=fim
    ).filter(dm.Q(s1=usuario) | dm.Q(s2=usuario))

    total_s1 = escalas.filter(s1=usuario).count()
    total_s2 = escalas.filter(s2=usuario).count()

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

    return {
        'usuario': usuario,
        'grupo': usuario.grupo.nome,
        'total_plantoes': total_s1 + total_s2,
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
