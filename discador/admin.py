from django.contrib import admin

from discador.models import (
    Blacklist,
    ConfiguracaoAPI,
    ImportacaoAPI,
    LigacaoImportada,
    ProcessamentoBase,
    RegraReciclagem,
)


@admin.register(ConfiguracaoAPI)
class ConfiguracaoAPIAdmin(admin.ModelAdmin):
    list_display = ('nome', 'base_url', 'is_active', 'updated_at')
    list_filter = ('is_active',)
    search_fields = ('nome', 'base_url')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RegraReciclagem)
class RegraReciclagemAdmin(admin.ModelAdmin):
    list_display = ('qualificacao', 'acao', 'tipo_bloqueio', 'prioridade', 'is_active', 'updated_at')
    list_filter = ('acao', 'tipo_bloqueio', 'is_active')
    search_fields = ('qualificacao', 'campanha_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LigacaoImportada)
class LigacaoImportadaAdmin(admin.ModelAdmin):
    list_display = (
        'call_id', 'telefone_normalizado', 'campanha_nome', 'qualificacao',
        'status', 'data_ligacao', 'created_at',
    )
    list_filter = ('status', 'qualificacao', 'campanha_id')
    search_fields = ('call_id', 'telefone_normalizado', 'telefone_original', 'agente_nome')
    readonly_fields = ('created_at', 'payload_original')
    date_hierarchy = 'data_ligacao'


@admin.register(Blacklist)
class BlacklistAdmin(admin.ModelAdmin):
    list_display = (
        'telefone_normalizado', 'qualificacao_origem', 'tipo_bloqueio',
        'origem', 'is_active', 'bloqueado_em', 'bloqueado_ate',
    )
    list_filter = ('origem', 'tipo_bloqueio', 'is_active')
    search_fields = ('telefone_normalizado', 'telefone_original', 'cpf', 'call_id')
    readonly_fields = ('created_at', 'payload_original')
    date_hierarchy = 'bloqueado_em'


@admin.register(ImportacaoAPI)
class ImportacaoAPIAdmin(admin.ModelAdmin):
    """Histórico de importações — somente leitura no admin."""

    list_display = (
        'id', 'status', 'periodo_inicial', 'periodo_final',
        'total_ligacoes', 'total_bloqueios', 'criado_por', 'created_at',
    )
    list_filter = ('status',)
    search_fields = ('campanhas', 'log')
    readonly_fields = (
        'data_inicio', 'data_fim', 'periodo_inicial', 'periodo_final', 'campanhas',
        'total_ligacoes', 'total_com_qualificacao', 'total_bloqueios', 'total_ignorados',
        'total_erros', 'status', 'log', 'criado_por', 'created_at', 'finalizado_em',
    )
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProcessamentoBase)
class ProcessamentoBaseAdmin(admin.ModelAdmin):
    """Processamentos de bases CSV — somente leitura no admin."""

    list_display = (
        'nome', 'campanha_destino', 'status', 'total_linhas',
        'total_liberadas', 'total_bloqueadas', 'criado_por', 'created_at',
    )
    list_filter = ('status',)
    search_fields = ('nome', 'campanha_destino', 'log')
    readonly_fields = (
        'nome', 'campanha_destino', 'arquivo_original', 'arquivo_reciclado',
        'arquivo_bloqueados', 'coluna_telefone', 'coluna_cpf', 'total_linhas',
        'total_liberadas', 'total_bloqueadas', 'total_duplicadas', 'total_erros',
        'status', 'log', 'criado_por', 'created_at', 'finalizado_em',
    )
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
