from django.db import models
from django.contrib.auth.models import AbstractUser, UserManager
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.conf import settings


class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)


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
        IT_USER = 'IT_USER', 'Membro da Equipe (TI)'
        SUPERVISOR = 'SUPERVISOR', 'Supervisor'
        TEAM_LEADER = 'TEAM_LEADER', 'Líder de Equipe'
        MULTIPLIER = 'MULTIPLIER', 'Multiplicador'
        STANDARD = 'STANDARD', 'Usuário Padrão'

    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.STANDARD,
        help_text='Papel do usuário no sistema (define permissões de acesso).'
    )
    equipes = models.ManyToManyField(
        Equipe,
        blank=True,
        related_name='membros',
        help_text='Equipes do usuário (opcional; atribuída pelo administrador).',
    )

    objects = CustomUserManager()

    # Controle de auditoria
    created_at = models.DateTimeField(auto_now_add=True, help_text='Data e hora de criação.')
    updated_at = models.DateTimeField(auto_now=True, help_text='Data e hora da última atualização.')

    def __str__(self) -> str:
        """
        Retorna a representação em string do usuário.
        """
        return self.username


class RegistroAcao(models.Model):
    """Registro append-only de ações do sistema para auditoria."""

    class ModuloChoices(models.TextChoices):
        HELPDESK = 'helpdesk', 'Helpdesk'
        CHIPS = 'chips', 'Chips'
        EMAILS = 'emails', 'E-mails'
        EQUIPMENT = 'equipment', 'Equipamentos'
        CORE = 'core', 'Core'

    class AcaoChoices(models.TextChoices):
        CREATED = 'CREATED', 'Criação'
        UPDATED = 'UPDATED', 'Atualização'
        STATUS_CHANGED = 'STATUS_CHANGED', 'Mudança de status'
        ASSIGNED = 'ASSIGNED', 'Atribuição'
        TRANSFERRED = 'TRANSFERRED', 'Transferência'
        RETURNED = 'RETURNED', 'Devolução'
        DELIVERY = 'DELIVERY', 'Entrega'
        COMMENT = 'COMMENT', 'Comentário'
        ACTIVATED = 'ACTIVATED', 'Ativação'
        DEACTIVATED = 'DEACTIVATED', 'Desativação'
        PASSWORD_RESET = 'PASSWORD_RESET', 'Reset de senha'
        RECHARGE = 'RECHARGE', 'Recarga'
        BLOCKED = 'BLOCKED', 'Bloqueio'
        UNBLOCKED = 'UNBLOCKED', 'Desbloqueio'
        DELETED = 'DELETED', 'Exclusão'

    modulo = models.CharField(max_length=20, choices=ModuloChoices.choices, db_index=True)
    acao = models.CharField(max_length=30, choices=AcaoChoices.choices, db_index=True)
    descricao = models.TextField(help_text='Descrição legível da ação.')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acoes_registradas',
        help_text='Usuário que executou a ação.',
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    object_repr = models.CharField(max_length=255, blank=True, help_text='Snapshot do objeto afetado.')
    metadata = models.JSONField(default=dict, blank=True, help_text='Detalhes estruturados (antes/depois).')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'registro de ação'
        verbose_name_plural = 'registros de ação'
        indexes = [
            models.Index(fields=['modulo', '-timestamp'], name='core_regist_modulo__idx'),
            models.Index(fields=['actor', '-timestamp'], name='core_regist_actor_i_idx'),
        ]

    def __str__(self) -> str:
        return f'[{self.get_modulo_display()}] {self.get_acao_display()} — {self.descricao[:60]}'
