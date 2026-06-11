from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class TicketCategory(models.Model):
    """Categoria de chamado configurável (ex.: Hardware, Software)."""
    name = models.CharField(max_length=80, unique=True, help_text='Nome exibido da categoria.')
    is_active = models.BooleanField(default=True, help_text='Categorias inativas não aparecem no formulário.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'categoria de chamado'
        verbose_name_plural = 'categorias de chamado'

    def __str__(self) -> str:
        return self.name


class Ticket(models.Model):
    """
    Modelo que representa um chamado (Ticket) de Helpdesk.
    Utilizado para o Kanban e controle de tarefas da TI.
    """
    class StatusChoices(models.TextChoices):
        NEW = 'NEW', 'Novos'
        IN_PROGRESS = 'IN_PROGRESS', 'Em Atendimento'
        PENDING = 'PENDING', 'Pendente'
        RESOLVED = 'RESOLVED', 'Resolvido'

    class PriorityChoices(models.TextChoices):
        LOW = 'LOW', 'Baixa'
        MEDIUM = 'MEDIUM', 'Média'
        HIGH = 'HIGH', 'Alta'
        URGENT = 'URGENT', 'Urgente'
        
    title = models.CharField(max_length=200, help_text='Título ou resumo do problema.')
    description = models.TextField(help_text='Descrição detalhada do chamado.')
    
    status = models.CharField(
        max_length=20, 
        choices=StatusChoices.choices, 
        default=StatusChoices.NEW,
        help_text='Coluna atual do cartão no Kanban.'
    )
    priority = models.CharField(
        max_length=20,
        choices=PriorityChoices.choices,
        null=True,
        blank=True,
        help_text='Definida pela TI; null até triagem.',
    )
    category = models.ForeignKey(
        TicketCategory,
        on_delete=models.PROTECT,
        related_name='tickets',
        help_text='Categoria do problema.',
    )
    
    requester_name = models.CharField(
        max_length=150, 
        help_text='Nome do solicitante (ex: vindo do WhatsApp).'
    )

    requester_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='requested_tickets',
        help_text='Usuário do sistema selecionado como solicitante.',
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_tickets',
        help_text='Usuário que abriu o chamado no sistema.',
    )
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tickets',
        help_text='Técnico responsável pelo chamado.'
    )
    
    # Soft delete, arquivamento e timestamps
    is_active = models.BooleanField(default=True, help_text='Indica se o registro está ativo (Soft delete).')
    is_archived = models.BooleanField(default=False, help_text='Indica se o chamado foi arquivado após um tempo resolvido.')
    created_at = models.DateTimeField(auto_now_add=True, help_text='Data e hora de criação.')
    updated_at = models.DateTimeField(auto_now=True, help_text='Data e hora da última atualização.')

    @classmethod
    def archive_old_resolved_tickets(cls, days=2):
        """
        Arquiva tickets que estão no status RESOLVED há mais de 'days' dias.
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        cls.objects.filter(
            status=cls.StatusChoices.RESOLVED,
            is_archived=False,
            updated_at__lt=cutoff_date
        ).update(is_archived=True)

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old_status = Ticket.objects.only('status').get(pk=self.pk).status
                if old_status != self.status:
                    self.is_archived = False
            except Ticket.DoesNotExist:
                pass
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"[{self.get_status_display()}] {self.title} - {self.requester_name}"


class Comment(models.Model):
    """
    Modelo de comentários e histórico de iterações em um ticket.
    """
    ticket = models.ForeignKey(
        Ticket, 
        on_delete=models.CASCADE, 
        related_name='comments',
        help_text='Chamado ao qual o comentário pertence.'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        help_text='Usuário que fez o comentário (ou None se for do sistema).'
    )
    text = models.TextField(help_text='Texto do comentário ou atualização do histórico.')
    
    # Soft delete e timestamps
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Comentário de {self.author} em {self.ticket.title}"
