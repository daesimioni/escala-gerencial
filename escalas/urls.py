"""
URL configuration for escalas app.
"""
from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('calendario/', views.calendario, name='calendario'),
    path('calendario/<int:ano>/<int:mes>/', views.calendario, name='calendario_mes'),
    path('calendario/anual/', views.calendario_anual, name='calendario_anual'),
    path('calendario/anual/<int:ano>/', views.calendario_anual, name='calendario_anual'),
    path('dia/<int:ano>/<int:mes>/<int:dia>/editar/', views.editar_dia, name='editar_dia'),
    path('dia/<int:ano>/<int:mes>/<int:dia>/limpar/', views.limpar_dia, name='limpar_dia'),
    path('usuarios/', views.usuarios, name='usuarios'),
    path('usuarios/<int:pk>/editar/', views.editar_usuario, name='editar_usuario'),
    path('bloqueios/', views.bloqueios, name='bloqueios'),
    path('bloqueios/adicionar/', views.adicionar_bloqueio, name='adicionar_bloqueio'),
    path('bloqueios/<int:pk>/editar/', views.editar_bloqueio, name='editar_bloqueio'),
    path('bloqueios/<int:pk>/remover/', views.remover_bloqueio, name='remover_bloqueio'),
    path('feriados/', views.feriados, name='feriados'),
    path('feriados/adicionar/', views.adicionar_feriado, name='adicionar_feriado'),
    path('feriados/<int:pk>/editar/', views.editar_feriado, name='editar_feriado'),
    path('feriadoes/', views.feriadoes, name='feriadoes'),
    path('feriadoes/adicionar/', views.adicionar_feriadao, name='adicionar_feriadao'),
    path('gerar-escala/', views.gerar_escala, name='gerar_escala'),
    path('trocar-escala/', views.trocar_escala, name='trocar_escala'),
    path('trocar-escala/<int:pk>/aceitar/', views.aceitar_solicitacao_troca, name='aceitar_solicitacao_troca'),
    path('trocar-escala/<int:pk>/recusar/', views.recusar_solicitacao_troca, name='recusar_solicitacao_troca'),
    path('trocar-escala/<int:pk>/aprovar/', views.aprovar_solicitacao_troca, name='aprovar_solicitacao_troca'),
    path('trocar-escala/<int:pk>/rejeitar/', views.rejeitar_solicitacao_troca, name='rejeitar_solicitacao_troca'),
    path('relatorios/', views.relatorios, name='relatorios'),
    path('relatorios/exportar-csv/', views.exportar_csv, name='exportar_csv'),
    path('relatorios/exportar-csv/resumo-mensal/', views.exportar_resumo_csv, name='exportar_resumo_csv'),
    path('relatorios/exportar-csv/resumo-anual/', views.exportar_resumo_csv, name='exportar_resumo_anual_csv'),
    path('exportar/', views.exportar, name='exportar'),
    path('fechar-mes/<int:ano>/<int:mes>/', views.fechar_mes_view, name='fechar_mes'),
    path('reabrir-mes/<int:ano>/<int:mes>/', views.reabrir_mes_view, name='reabrir_mes'),
]
