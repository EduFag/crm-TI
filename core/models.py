from django.db import models
from django.contrib.auth.models import AbstractUser

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
    
    # Controle de auditoria
    created_at = models.DateTimeField(auto_now_add=True, help_text='Data e hora de criação.')
    updated_at = models.DateTimeField(auto_now=True, help_text='Data e hora da última atualização.')

    def __str__(self) -> str:
        """
        Retorna a representação em string do usuário.
        """
        return self.username
