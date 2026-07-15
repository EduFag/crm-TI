from django.contrib import admin

from integracoes.models import IntegracaoIA


@admin.register(IntegracaoIA)
class IntegracaoIAAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'is_active', 'token_hint', 'created_at')
    list_filter = ('provider', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('credentials_encrypted', 'token_hint', 'created_at', 'updated_at')
