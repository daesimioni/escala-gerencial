"""
Views for the Escala de Sobreaviso system.
"""
import csv
import json
from calendar import monthrange
from collections import defaultdict
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models as dm
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    BloqueioUsuarioForm, EscalaDiaForm, FeriadoForm, FeriadaoForm,
    GeracaoEscalaForm, TrocaEscalaForm,
)
from .models import (
    AlertaSistema, BloqueioUsuario, ConfiguracaoSistema, EscalaBloco,
    EscalaDia, Feriado, Feriadao, GrupoEscala, HistoricoAlteracao,
    MesFechado, UsuarioEscala,
)
from .services import (
    analisar_impacto_ferias, fechar_mes, gerar_escala_mensal,
    gerar_escala_anual, gerar_escala_periodo, get_alertas_desequilibrio,
    get_blocos_cobertura, get_meses_fechados, get_relatorio_usuarios,
    is_mes_fechado, reabrir_mes, regenerar_apos_data,
    validar_dia, _atualizar_contadores_usuarios,
)


def _get_calendar_context(ano, mes):
    """Build calendar data for a given month."""
    primeiro_dia = date(ano, mes, 1)
    ultimo_dia = date(ano, mes, monthrange(ano, mes)[1])
    dow_inicio = primeiro_dia.weekday()  # 0=Mon, 6=Sun

    # Adjust to start on Sunday (Brazilian convention)
    dow_inicio = (dow_inicio + 1) % 7  # Now 0=Sun

    # Build day list
    days_in_month = monthrange(ano, mes)[1]
    days = []

    # Previous month filler
    if dow_inicio > 0:
        prev_mes = mes - 1 if mes > 1 else 12
        prev_ano = ano if mes > 1 else ano - 1
        prev_days = monthrange(prev_ano, prev_mes)[1]
        for i in range(dow_inicio):
            d = prev_days - dow_inicio + i + 1
            days.append({'date': date(prev_ano, prev_mes, d), 'other_month': True})

    # Current month
    for d in range(1, days_in_month + 1):
        days.append({'date': date(ano, mes, d), 'other_month': False})

    # Next month filler
    remaining = (7 - (len(days) % 7)) % 7
    next_mes = mes + 1 if mes < 12 else 1
    next_ano = ano if mes < 12 else ano + 1
    for d in range(1, remaining + 1):
        days.append({'date': date(next_ano, next_mes, d), 'other_month': True})

    # Load assignments
    assignments = {}
    for ed in EscalaDia.objects.filter(data__year=ano, data__month=mes).select_related('s1', 's2', 's1__grupo', 's2__grupo'):
        assignments[ed.data] = ed

    # Load blocks
    blocos_usuarios = {}
    for blk in BloqueioUsuario.objects.select_related('usuario'):
        cursor = blk.data_inicio
        while cursor <= blk.data_fim:
            if cursor.month == mes and cursor.year == ano:
                if cursor not in blocos_usuarios:
                    blocos_usuarios[cursor] = []
                blocos_usuarios[cursor].append(blk)
            cursor += timedelta(days=1)

    # Group days into weeks
    weeks = []
    week = []
    for day_info in days:
        d = day_info['date']
        day_info['dow'] = d.weekday()  # 0=Mon
        day_info['is_weekend'] = d.weekday() in (5, 6)
        day_info['is_today'] = d == date.today()
        day_info['assignment'] = assignments.get(d)
        day_info['blocks'] = blocos_usuarios.get(d, [])
        day_info['has_conflict'] = day_info['assignment'].tem_conflito if day_info.get('assignment') else False

        # Determine day type for visual
        ed = assignments.get(d)
        if ed:
            if ed.feriadao:
                day_info['day_type'] = 'feriadao'
            elif ed.feriado:
                day_info['day_type'] = 'feriado'
            elif ed.fim_de_semana:
                day_info['day_type'] = 'fim_de_semana'
            else:
                day_info['day_type'] = 'comum'
        else:
            day_info['day_type'] = 'fim_de_semana' if day_info['is_weekend'] else 'comum'

        week.append(day_info)
        if len(week) == 7:
            weeks.append(week)
            week = []

    return {
        'weeks': weeks,
        'ano': ano,
        'mes': mes,
        'nome_mes': _nome_mes(mes),
        'mes_anterior': (mes - 1 if mes > 1 else 12, ano if mes > 1 else ano - 1),
        'mes_seguinte': (mes + 1 if mes < 12 else 1, ano if mes < 12 else ano + 1),
    }


def _nome_mes(mes):
    nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    return nomes[mes - 1]


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Home page with summary stats and quick links."""
    total_usuarios = UsuarioEscala.objects.filter(ativo=True).count()
    total_bloqueios = BloqueioUsuario.objects.count()
    hoje = date.today()
    escala_hoje = EscalaDia.objects.filter(data=hoje).first()
    alertas = get_alertas_desequilibrio()

    # System alerts (unresolved)
    alertas_sistema = AlertaSistema.objects.filter(resolvido=False).order_by('-created_at')[:10]

    # Upcoming coverage
    blocos_proximos = get_blocos_cobertura(hoje.year, hoje.month)[:5]

    # Locked months
    meses_fechados = MesFechado.objects.all().order_by('ano', 'mes')

    # Users on vacation now
    usuarios_ferias = BloqueioUsuario.objects.filter(
        tipo='FERIAS',
        data_inicio__lte=hoje,
        data_fim__gte=hoje,
    ).select_related('usuario')

    ctx = {
        'total_usuarios': total_usuarios,
        'total_bloqueios': total_bloqueios,
        'escala_hoje': escala_hoje,
        'alertas': alertas,
        'alertas_sistema': alertas_sistema,
        'blocos_proximos': blocos_proximos,
        'hoje': hoje,
        'meses_fechados': meses_fechados,
        'usuarios_ferias': usuarios_ferias,
    }
    return render(request, 'escalas/dashboard.html', ctx)


# ─── Calendar ────────────────────────────────────────────────────────────────

@login_required
def calendario(request, ano=None, mes=None):
    """Monthly calendar view."""
    hoje = date.today()
    if ano is None:
        ano = hoje.year
    if mes is None:
        mes = hoje.month

    ctx = _get_calendar_context(ano, mes)
    ctx['usuarios'] = UsuarioEscala.objects.filter(ativo=True).select_related('grupo')
    ctx['grupos'] = GrupoEscala.objects.all()
    ctx['mes_fechado'] = is_mes_fechado(ano, mes)
    ctx['user_is_staff'] = request.user.is_staff

    # Summary table
    from .services import calcular_resumo_mensal
    ctx['resumo'] = calcular_resumo_mensal(ano, mes)
    ctx['media_plantoes'] = (
        sum(r['total_plantoes'] for r in ctx['resumo']) / max(len(ctx['resumo']), 1)
    )

    return render(request, 'escalas/calendario.html', ctx)


@login_required
def calendario_anual(request, ano=None):
    """Annual calendar overview."""
    if ano is None:
        ano = date.today().year

    meses_data = []
    for mes in range(1, 13):
        ctx = _get_calendar_context(ano, mes)
        # Count assignments
        dias_com_escala = EscalaDia.objects.filter(data__year=ano, data__month=mes).count()
        dias_sem_escala = sum(
            1 for w in ctx['weeks'] for d in w
            if not d['other_month'] and d['day_type'] != 'comum' and not d.get('assignment')
        )
        meses_data.append({
            'mes': mes,
            'nome': _nome_mes(mes),
            'dias_com_escala': dias_com_escala,
            'dias_sem_escala': dias_sem_escala,
            'weeks': ctx['weeks'],
        })

    from .services import calcular_resumo_anual
    resumo_anual = calcular_resumo_anual(ano)
    media_anual = sum(r['total_plantoes'] for r in resumo_anual) / max(len(resumo_anual), 1)

    return render(request, 'escalas/calendario_anual.html', {
        'ano': ano,
        'meses': meses_data,
        'ano_anterior': ano - 1,
        'ano_seguinte': ano + 1,
        'resumo': resumo_anual,
        'media_plantoes': media_anual,
    })


# ─── Day Editing ─────────────────────────────────────────────────────────────

@login_required
def editar_dia(request, ano, mes, dia):
    """Edit the on-call manager for a specific day."""
    data = date(ano, mes, dia)
    escala = EscalaDia.objects.filter(data=data).first()

    if request.method == 'POST':
        form = EscalaDiaForm(request.POST, instance=escala)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.data = data

            instance.s2 = None
            instance.manual = True
            instance.status = 'MANUAL'

            # Validate
            problemas = validar_dia(data, instance.s1, instance.s2)
            erros = [p for p in problemas if p['tipo'] == 'erro']
            alertas = [p for p in problemas if p['tipo'] == 'alerta']

            if erros:
                for e in erros:
                    messages.error(request, e['msg'])
                return redirect('calendario_mes', ano=ano, mes=mes)

            instance.editado_por = request.user
            instance.editado_em = timezone.now()
            instance.save()

            # Log
            HistoricoAlteracao.objects.create(
                usuario=request.user,
                tipo='EDICAO_DIA',
                descricao=f'Edição do dia {data}',
                dados_novos={'s1': instance.s1_id, 'manual': True},
            )

            for a in alertas:
                messages.warning(request, a['msg'])

            messages.success(request, f'Escala do dia {data} atualizada.')
            return redirect('calendario_mes', ano=ano, mes=mes)
    else:
        form = EscalaDiaForm(instance=escala)

    return render(request, 'escalas/editar_dia.html', {
        'form': form,
        'data': data,
        'escala': escala,
    })


@login_required
def limpar_dia(request, ano, mes, dia):
    """Clear the on-call manager for a day."""
    data = date(ano, mes, dia)
    if request.method == 'POST':
        EscalaDia.objects.filter(data=data).delete()
        HistoricoAlteracao.objects.create(
            usuario=request.user,
            tipo='EDICAO_DIA',
            descricao=f'Limpeza do dia {data}',
        )
        messages.success(request, f'Escala do dia {data} removida.')
    return redirect('calendario_mes', ano=ano, mes=mes)


# ─── Users ───────────────────────────────────────────────────────────────────

@login_required
def usuarios(request):
    """List all escala users."""
    usuarios_list = UsuarioEscala.objects.select_related('grupo').all()
    return render(request, 'escalas/usuarios.html', {'usuarios': usuarios_list})


@login_required
def editar_usuario(request, pk):
    """Edit user details."""
    usuario = get_object_or_404(UsuarioEscala, pk=pk)
    if request.method == 'POST':
        usuario.nome = request.POST.get('nome', usuario.nome)
        usuario.ativo = request.POST.get('ativo') == 'on'
        grupo_id = request.POST.get('grupo')
        if grupo_id:
            usuario.grupo = get_object_or_404(GrupoEscala, pk=grupo_id)
        usuario.save()
        messages.success(request, f'Usuário {usuario.nome} atualizado.')
        return redirect('usuarios')

    grupos = GrupoEscala.objects.all()
    return render(request, 'escalas/usuario_form.html', {
        'usuario': usuario,
        'grupos': grupos,
    })


# ─── Blocks (Férias / Indisponibilidade) ─────────────────────────────────────

@login_required
def bloqueios(request):
    """List all user blocks."""
    bloqueios_list = BloqueioUsuario.objects.select_related('usuario').all()
    return render(request, 'escalas/bloqueios.html', {'bloqueios': bloqueios_list})


@login_required
def adicionar_bloqueio(request):
    """Add a new block for a user."""
    if request.method == 'POST':
        form = BloqueioUsuarioForm(request.POST)
        if form.is_valid():
            blk = form.save()
            HistoricoAlteracao.objects.create(
                usuario=request.user,
                tipo='ADICAO_BLOQUEIO',
                descricao=f'{blk.get_tipo_display()} para {blk.usuario.nome}: {blk.data_inicio} a {blk.data_fim}',
            )
            # Regenerate affected period
            criados, erros = regenerar_apos_data(blk.data_inicio, request.user)
            messages.success(request, f'Bloqueio adicionado. Escala regenerada: {criados} dias.')
            if erros:
                for e in erros:
                    messages.warning(request, e)
            return redirect('bloqueios')
    else:
        form = BloqueioUsuarioForm()

    return render(request, 'escalas/bloqueio_form.html', {'form': form, 'titulo': 'Adicionar Bloqueio'})


@login_required
def editar_bloqueio(request, pk):
    """Edit an existing block."""
    blk = get_object_or_404(BloqueioUsuario, pk=pk)
    if request.method == 'POST':
        form = BloqueioUsuarioForm(request.POST, instance=blk)
        if form.is_valid():
            form.save()
            regenerar_apos_data(blk.data_inicio, request.user)
            messages.success(request, 'Bloqueio atualizado. Escala regenerada.')
            return redirect('bloqueios')
    else:
        form = BloqueioUsuarioForm(instance=blk)

    return render(request, 'escalas/bloqueio_form.html', {'form': form, 'titulo': 'Editar Bloqueio'})


@login_required
def remover_bloqueio(request, pk):
    """Remove a block."""
    blk = get_object_or_404(BloqueioUsuario, pk=pk)
    if request.method == 'POST':
        data_inicio = blk.data_inicio
        blk.delete()
        HistoricoAlteracao.objects.create(
            usuario=request.user,
            tipo='REMOCAO_BLOQUEIO',
            descricao=f'Remoção de bloqueio',
        )
        regenerar_apos_data(data_inicio, request.user)
        messages.success(request, 'Bloqueio removido. Escala regenerada.')
    return redirect('bloqueios')


# ─── Holidays ────────────────────────────────────────────────────────────────

@login_required
def feriados(request):
    """List all holidays."""
    feriados_list = Feriado.objects.all().order_by('data')
    return render(request, 'escalas/feriados.html', {'feriados': feriados_list})


@login_required
def adicionar_feriado(request):
    """Add a new holiday."""
    if request.method == 'POST':
        form = FeriadoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Feriado adicionado.')
            return redirect('feriados')
    else:
        form = FeriadoForm(initial={'data': date.today()})

    return render(request, 'escalas/feriado_form.html', {'form': form, 'titulo': 'Adicionar Feriado'})


@login_required
def editar_feriado(request, pk):
    """Edit a holiday."""
    feriado = get_object_or_404(Feriado, pk=pk)
    if request.method == 'POST':
        form = FeriadoForm(request.POST, instance=feriado)
        if form.is_valid():
            form.save()
            messages.success(request, 'Feriado atualizado.')
            return redirect('feriados')
    else:
        form = FeriadoForm(instance=feriado)

    return render(request, 'escalas/feriado_form.html', {'form': form, 'titulo': 'Editar Feriado'})


# ─── Feriadões ───────────────────────────────────────────────────────────────

@login_required
def feriadoes(request):
    """List all feriadão blocks."""
    feriadoes_list = Feriadao.objects.all().order_by('data_inicio')
    return render(request, 'escalas/feriadoes.html', {'feriadoes': feriadoes_list})


@login_required
def adicionar_feriadao(request):
    """Manually add a feriadão block."""
    if request.method == 'POST':
        form = FeriadaoForm(request.POST)
        if form.is_valid():
            fd = form.save(commit=False)
            fd.manual = True
            fd.save()
            messages.success(request, 'Feriadão adicionado manualmente.')
            return redirect('feriadoes')
    else:
        form = FeriadaoForm(initial={'manual': True})

    return render(request, 'escalas/feriado_form.html', {'form': form, 'titulo': 'Adicionar Feriadão Manual'})


# ─── Scale Generation ────────────────────────────────────────────────────────
# ─── Shift Swap ──────────────────────────────────────────────────────────────


@login_required
def trocar_escala(request):
    """Replace the on-call manager on a given date."""
    if request.method == 'POST':
        form = TrocaEscalaForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data['data']
            destino = form.cleaned_data['usuario_destino']

            escala = EscalaDia.objects.filter(data=data).first()
            if not escala:
                messages.error(request, f'Não há escala cadastrada para {data}.')
                return redirect('trocar_escala')

            anterior_id = escala.s1_id
            problemas = validar_dia(data, destino, None)
            erros = [p for p in problemas if p['tipo'] == 'erro']
            if erros:
                for e in erros:
                    messages.error(request, e['msg'])
                return redirect('trocar_escala')

            escala.s1 = destino
            escala.s2 = None
            escala.manual = True
            escala.status = 'MANUAL'
            escala.editado_por = request.user
            escala.editado_em = timezone.now()
            escala.save()
            _atualizar_contadores_usuarios()

            HistoricoAlteracao.objects.create(
                usuario=request.user,
                tipo='TROCA_ESCALA',
                descricao=f'Troca em {data}: novo sobreaviso {destino.nome}',
                dados_anteriores={'s1': anterior_id},
                dados_novos={'s1': destino.id},
            )

            messages.success(request, f'Sobreaviso atualizado para {data}.')
            return redirect('calendario_mes', ano=data.year, mes=data.month)
    else:
        form = TrocaEscalaForm(initial={'data': date.today()})

    return render(request, 'escalas/trocar_escala.html', {'form': form})


# ─── Reports ─────────────────────────────────────────────────────────────────

@login_required
def relatorios(request):
    """Reports dashboard."""
    ano = request.GET.get('ano', str(date.today().year))
    mes = request.GET.get('mes', '')

    filtro_ano = int(ano) if ano else None
    filtro_mes = int(mes) if mes else None

    relatorio = get_relatorio_usuarios(filtro_ano, filtro_mes)
    alertas = get_alertas_desequilibrio()

    meses_nomes = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho',
                   'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
    meses_disponiveis = [(i, meses_nomes[i-1]) for i in range(1, 13)]

    return render(request, 'escalas/relatorios.html', {
        'relatorio': relatorio,
        'alertas': alertas,
        'ano': filtro_ano,
        'mes': filtro_mes,
        'anos_disponiveis': range(2025, 2031),
        'meses_disponiveis': meses_disponiveis,
    })


@login_required
def exportar_csv(request):
    """Export monthly on-call schedule as CSV."""
    ano = int(request.GET.get('ano', date.today().year))
    mes = int(request.GET.get('mes', date.today().month))

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="escala_{ano}_{mes:02d}.csv"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['Data', 'Dia', 'Tipo', 'Gerente de Sobreaviso', 'Grupo', 'Manual', 'Observacao'])

    dia_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
    days_in_month = monthrange(ano, mes)[1]

    for d in range(1, days_in_month + 1):
        data = date(ano, mes, d)
        escala = EscalaDia.objects.filter(data=data).select_related('s1', 's1__grupo').first()

        tipo = 'Comum'
        if escala:
            if escala.feriadao:
                tipo = 'Feriadao'
            elif escala.feriado:
                tipo = 'Feriado'
            elif escala.fim_de_semana:
                tipo = 'FDS'

        gerente_nome = escala.s1.nome if escala and escala.s1 else ''
        gerente_grupo = escala.s1.grupo.nome if escala and escala.s1 else ''
        manual = 'Sim' if escala and escala.manual else 'Nao'
        obs = escala.observacao if escala else ''

        writer.writerow([data, dia_names[data.weekday()], tipo, gerente_nome, gerente_grupo, manual, obs])

    return response


@login_required
def exportar(request):
    """Export page."""
    return render(request, 'escalas/exportar.html')


# ─── Month Locking ───────────────────────────────────────────────────────────

@login_required
def exportar_resumo_csv(request):
    """Export summary table (monthly or annual) as CSV."""
    from .services import calcular_resumo_mensal, calcular_resumo_anual

    hoje = date.today()
    ano = int(request.GET.get('ano', hoje.year))
    mes = request.GET.get('mes')
    tipo = request.GET.get('tipo', 'mensal')

    if tipo == 'anual' or (not mes):
        dados = calcular_resumo_anual(ano)
        filename = f'resumo_anual_{ano}.csv'
    else:
        mes = int(mes)
        dados = calcular_resumo_mensal(ano, mes)
        filename = f'resumo_{ano}_{mes:02d}.csv'

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow([
        'Usuario', 'Grupo', 'Total Sobreaviso', 'Dias Disponiveis',
        'Sabados', 'Domingos', 'Feriados', 'Feriadoes',
        'Ferias (dias)', 'Bloqueios (dias)'
    ])

    for row in dados:
        writer.writerow([
            row['usuario'].nome,
            row['grupo'],
            row['total_plantoes'],
            row['dias_disponiveis'],
            row['sabados'],
            row['domingos'],
            row['feriados'],
            row['feriadoes'],
            row['ferias_dias'],
            row['bloqueios_dias'],
        ])

    return response


@login_required
def fechar_mes_view(request, ano, mes):
    """Lock/close a month — admin only."""
    if not request.user.is_staff:
        messages.error(request, 'Apenas administradores podem fechar meses.')
        return redirect('calendario_mes', ano=ano, mes=mes)

    if request.method == 'POST':
        status = request.POST.get('status', 'FECHADO')
        mf, created = fechar_mes(ano, mes, request.user, status)
        HistoricoAlteracao.objects.create(
            usuario=request.user,
            tipo='OUTRO',
            descricao=f'Fechamento do mês {mes:02d}/{ano} — status: {status}',
        )
        label = 'fechado' if created else 'já estava fechado'
        messages.success(request, f'Mês {mes:02d}/{ano} {label} com sucesso.')
    return redirect('calendario_mes', ano=ano, mes=mes)


@login_required
def reabrir_mes_view(request, ano, mes):
    """Reopen a locked month — admin only."""
    if not request.user.is_staff:
        messages.error(request, 'Apenas administradores podem reabrir meses.')
        return redirect('calendario_mes', ano=ano, mes=mes)

    if request.method == 'POST':
        reabrir_mes(ano, mes)
        HistoricoAlteracao.objects.create(
            usuario=request.user,
            tipo='OUTRO',
            descricao=f'Reabertura do mês {mes:02d}/{ano}',
        )
        messages.success(request, f'Mês {mes:02d}/{ano} reaberto. A escala pode ser regenerada.')
    return redirect('calendario_mes', ano=ano, mes=mes)


# ─── Updated Generation View ─────────────────────────────────────────────────

@login_required
def gerar_escala(request):
    """Trigger scale generation for a specific month or period."""
    if request.method == 'POST':
        form = GeracaoEscalaForm(request.POST)
        if form.is_valid():
            ano = form.cleaned_data['ano']
            mes = form.cleaned_data['mes']
            preservar = form.cleaned_data['preservar_manuais']

            # Check if month is locked
            if is_mes_fechado(ano, mes):
                messages.error(
                    request,
                    f'Mês {mes:02d}/{ano} está fechado. '
                    f'Apenas um administrador pode forçar a regeneração de meses fechados.'
                )
                return redirect('calendario_mes', ano=ano, mes=mes)

            criados, erros = gerar_escala_mensal(ano, mes, preservar, request.user)

            HistoricoAlteracao.objects.create(
                usuario=request.user,
                tipo='REGENERACAO',
                descricao=f'Regeneração da escala para {mes:02d}/{ano}',
            )

            messages.success(request, f'Escala gerada: {criados} dias para {mes:02d}/{ano}.')
            if erros:
                for e in erros:
                    messages.warning(request, e)

            return redirect('calendario_mes', ano=ano, mes=mes)
    else:
        hoje = date.today()
        form = GeracaoEscalaForm(initial={'ano': hoje.year, 'mes': hoje.month})

    meses_fechados = MesFechado.objects.all().order_by('-ano', '-mes')
    return render(request, 'escalas/gerar_escala.html', {
        'form': form,
        'meses_fechados': meses_fechados,
    })
