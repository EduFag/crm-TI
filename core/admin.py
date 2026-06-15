from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Equipe, RegistroAcao


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Configuração do painel administrativo do Django para o modelo CustomUser.
    Permite que o administrador crie e gerencie os usuários, atribuindo roles específicos.
    """
    model = CustomUser
    
    # Adicionando os novos campos na visualização e edição do painel admin
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Adicionais (RBAC)', {'fields': ('role', 'equipes')}),
        ('Auditoria', {'fields': ('created_at', 'updated_at')}),
    )
    
    # Adicionando os novos campos na tela de criação de usuário pelo painel admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informações Adicionais (RBAC)', {'fields': ('role', 'equipes')}),
    )
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'get_equipes', 'is_staff', 'is_active', 'created_at')
    list_filter = ('role', 'equipes', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    readonly_fields = ('created_at', 'updated_at')

    @admin.display(description='Equipes')
    def get_equipes(self, obj):
        return ", ".join([e.name for e in obj.equipes.all()])


@admin.register(RegistroAcao)
class RegistroAcaoAdmin(admin.ModelAdmin):
    """Auditoria somente leitura — registros nunca são editados pelo admin."""

    list_display = ('timestamp', 'modulo', 'acao', 'actor', 'object_repr', 'descricao_curta')
    list_filter = ('modulo', 'acao', 'timestamp')
    search_fields = ('descricao', 'object_repr', 'actor__username')
    readonly_fields = (
        'modulo', 'acao', 'descricao', 'actor', 'content_type', 'object_id',
        'object_repr', 'metadata', 'timestamp',
    )
    date_hierarchy = 'timestamp'

    @admin.display(description='Descrição')
    def descricao_curta(self, obj):
        return obj.descricao[:80]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
