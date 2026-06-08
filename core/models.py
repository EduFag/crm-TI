from django.db import models
from django.contrib.auth.models import AbstractUser


class Equipe(models.Model):
    """Equipe organizacional para agrupar usuários (ex.: Financeiro, Comercial)."""
    name = models.CharField(max_length=80, unique=True, help_text='Nome da equipe.')
    is_active = models.BooleanField(default=True, help_text='Equipes inativas não aparecem na atribuição.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'equipe'
        verbose_name_plural = 'equipes'

    def __str__(self) -> str:
        return self.name


class CustomUser(AbstractUser):
    """
    Modelo customizado de usuário estendendo o AbstractUser do Django.
    Este modelo incorpora permissões baseadas em roles (RBAC - Role-Based Access Control)
    e campos de controle de auditoria de data e hora, conforme o padrão do sistema.
    A exclusão lógica é feita utilizando o campo 'is_active' herdado do AbstractUser.
    """
    
    class RoleChoices(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        MANAGER = 'MANAGER', 'Gerente'
        USER = 'USER', 'Usuário Padrão'

    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.USER,
        help_text='Papel do usuário no sistema (define permissões de acesso).'
    )
    equipe = models.ForeignKey(
        Equipe,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='membros',
        help_text='Equipe do usuário (opcional; atribuída pelo administrador).',
    )

    # Controle de auditoria
    created_at = models.DateTimeField(auto_now_add=True, help_text='Data e hora de criação.')
    updated_at = models.DateTimeField(auto_now=True, help_text='Data e hora da última atualização.')

    def __str__(self) -> str:
        """
        Retorna a representação em string do usuário.
        """
        return self.username
