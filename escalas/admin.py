"""
Django Admin configuration for Escala de Sobreaviso.
"""
from django.contrib import admin

from .models import (
    BloqueioUsuario, ConfiguracaoSistema, EscalaBloco, EscalaDia,
    Feriado, Feriadao, GrupoEscala, HistoricoAlteracao, SolicitacaoTroca,
    UsuarioEscala,
)


@admin.register(GrupoEscala)
class GrupoEscalaAdmin(admin.ModelAdmin):
    list_display = ['nome', 'descricao']
    search_fields = ['nome']


@admin.register(UsuarioEscala)
class UsuarioEscalaAdmin(admin.ModelAdmin):
    list_display = [
        'nome', 'codigo_legado', 'lotacao', 'telefone', 'grupo', 'ativo',
        'fer_inicial', 'pl_inicial', 'oportunidades_iniciais',
        'total_s1', 'total_dias_sobreaviso',
        'feriadao_s1_count',
        'ultima_escala',
    ]
    list_filter = ['grupo', 'ativo']
    search_fields = ['nome', 'codigo_legado', 'lotacao', 'telefone']
    list_editable = ['ativo']


@admin.register(BloqueioUsuario)
class BloqueioUsuarioAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'tipo', 'data_inicio', 'data_fim', 'motivo']
    list_filter = ['tipo', 'data_inicio']
    search_fields = ['usuario__nome', 'motivo']


@admin.register(Feriado)
class FeriadoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'data', 'tipo', 'ativo', 'recorrente']
    list_filter = ['tipo', 'ativo', 'recorrente']
    search_fields = ['nome']
    list_editable = ['ativo']


@admin.register(Feriadao)
class FeriadaoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'data_inicio', 'data_fim', 'manual', 'total_dias']
    list_filter = ['manual']


@admin.register(EscalaDia)
class EscalaDiaAdmin(admin.ModelAdmin):
    list_display = ['data', 's1', 'fim_de_semana', 'feriado', 'feriadao', 'manual']
    list_filter = ['fim_de_semana', 'feriado', 'feriadao', 'manual']
    search_fields = ['s1__nome']
    date_hierarchy = 'data'


@admin.register(EscalaBloco)
class EscalaBlocoAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'nome', 'data_inicio', 'data_fim']
    list_filter = ['tipo']


@admin.register(SolicitacaoTroca)
class SolicitacaoTrocaAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'status', 'gerente_origem', 'data_origem',
        'gerente_destino', 'data_destino',
    ]
    list_filter = ['status', 'created_at']
    search_fields = ['gerente_origem__nome', 'gerente_destino__nome', 'motivo']
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(ordering='escala_origem__data')
    def data_origem(self, obj):
        return obj.escala_origem.data

    @admin.display(ordering='escala_destino__data')
    def data_destino(self, obj):
        return obj.escala_destino.data


@admin.register(HistoricoAlteracao)
class HistoricoAlteracaoAdmin(admin.ModelAdmin):
    list_display = ['tipo', 'usuario', 'descricao', 'created_at']
    list_filter = ['tipo', 'created_at']
    readonly_fields = ['usuario', 'tipo', 'descricao', 'dados_anteriores', 'dados_novos', 'created_at']


@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = ['chave', 'valor', 'descricao']
    search_fields = ['chave']
