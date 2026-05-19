from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """
    Configuração do painel administrativo do Django para o modelo CustomUser.
    Permite que o administrador crie e gerencie os usuários, atribuindo roles específicos.
    """
    model = CustomUser
    
    # Adicionando os novos campos na visualização e edição do painel admin
    fieldsets = UserAdmin.fieldsets + (
        ('Informações Adicionais (RBAC)', {'fields': ('role',)}),
        ('Auditoria', {'fields': ('created_at', 'updated_at')}),
    )
    
    # Adicionando os novos campos na tela de criação de usuário pelo painel admin
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informações Adicionais (RBAC)', {'fields': ('role',)}),
    )
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff', 'is_active', 'created_at')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    readonly_fields = ('created_at', 'updated_at')
