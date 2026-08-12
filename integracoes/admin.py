from django.contrib import admin

from integracoes.models import AssistenteInteracao, IntegracaoApi, IntegracaoIA, TokenApiExterna


@admin.register(IntegracaoIA)
class IntegracaoIAAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'is_active', 'token_hint', 'created_at')
    list_filter = ('provider', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('credentials_encrypted', 'token_hint', 'created_at', 'updated_at')


@admin.register(IntegracaoApi)
class IntegracaoApiAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'is_active', 'token_hint', 'created_at')
    list_filter = ('provider', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('credentials_encrypted', 'token_hint', 'created_at', 'updated_at')


@admin.register(TokenApiExterna)
class TokenApiExternaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'user', 'prefixo', 'ativo', 'criado_em', 'ultimo_uso')
    list_filter = ('ativo',)
    search_fields = ('nome', 'prefixo', 'user__username')
    readonly_fields = ('token_hash', 'prefixo', 'criado_em', 'ultimo_uso')


@admin.register(AssistenteInteracao)
class AssistenteInteracaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket_id', 'hybrid', 'nota', 'criado_em', 'nota_por')
    list_filter = ('nota', 'hybrid')
    search_fields = ('ticket_id', 'comentario')
    readonly_fields = ('ticket_id', 'chunk_ids', 'hybrid', 'criado_em', 'nota_em')
