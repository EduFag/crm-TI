from django.contrib import admin

from discador.models import (
    AcessoDiscador,
    Campanha,
    Discador,
    DiscadorContratoHistorico,
    Ramal,
    RamalAtribuicaoHistorico,
)


@admin.register(Discador)
class DiscadorAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 'slug', 'licencas_contratadas', 'valor_por_licenca',
        'is_active', 'updated_at',
    )
    list_filter = ('is_active',)
    search_fields = ('nome', 'slug')
    prepopulated_fields = {'slug': ('nome',)}


@admin.register(DiscadorContratoHistorico)
class DiscadorContratoHistoricoAdmin(admin.ModelAdmin):
    list_display = (
        'discador', 'licencas_contratadas', 'valor_por_licenca',
        'registered_by', 'timestamp',
    )
    list_filter = ('discador',)
    readonly_fields = (
        'discador', 'valor_por_licenca', 'licencas_contratadas',
        'observacao', 'registered_by', 'timestamp',
    )
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Campanha)
class CampanhaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'discador', 'is_active', 'created_at')
    list_filter = ('discador', 'is_active')
    search_fields = ('nome',)


@admin.register(Ramal)
class RamalAdmin(admin.ModelAdmin):
    list_display = ('numero', 'discador', 'status', 'created_at')
    list_filter = ('discador', 'status')
    search_fields = ('numero',)


@admin.register(AcessoDiscador)
class AcessoDiscadorAdmin(admin.ModelAdmin):
    list_display = (
        'titular_nome', 'login_discador', 'ramal', 'campanha',
        'tipo', 'status', 'discador',
    )
    list_filter = ('discador', 'tipo', 'status')
    search_fields = ('titular_nome', 'login_discador', 'ramal__numero')
    raw_id_fields = ('titular_user',)


@admin.register(RamalAtribuicaoHistorico)
class RamalAtribuicaoHistoricoAdmin(admin.ModelAdmin):
    list_display = (
        'ramal', 'action', 'titular_nome', 'login_discador',
        'status', 'registered_by', 'timestamp',
    )
    list_filter = ('action', 'status')
    search_fields = ('ramal__numero', 'titular_nome', 'login_discador')
    readonly_fields = (
        'ramal', 'action', 'titular_nome', 'login_discador',
        'campanha_nome', 'tipo', 'status', 'observacao',
        'registered_by', 'timestamp',
    )
    date_hierarchy = 'timestamp'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
