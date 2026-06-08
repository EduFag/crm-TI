from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Equipe


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
        ('Informações Adicionais (RBAC)', {'fields': ('role', 'equipe')}),
        ('Auditoria', {'fields': ('created_at', 'updated_at')}),
    )
    
    # Adicionando os novos campos na tela de criação de usuário pelo painel admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informações Adicionais (RBAC)', {'fields': ('role', 'equipe')}),
    )
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'equipe', 'is_staff', 'is_active', 'created_at')
    list_filter = ('role', 'equipe', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    readonly_fields = ('created_at', 'updated_at')
