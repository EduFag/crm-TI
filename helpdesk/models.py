from django.db import models
from django.db.models import Q, OuterRef, Subquery, DateTimeField, Case, When
from django.db.models.functions import Coalesce, Least
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


class TicketSpecificCategory(models.Model):
    """Categoria específica do chamado definida pela TI (ex.: Troca de fonte, Instalação de software)."""
    name = models.CharField(max_length=80, unique=True, help_text='Nome exibido da categoria específica.')
    is_active = models.BooleanField(default=True, help_text='Categorias inativas não aparecem no formulário.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'categoria específica'
        verbose_name_plural = 'categorias específicas'

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
    specific_category = models.ForeignKey(
        TicketSpecificCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='tickets',
        help_text='Categoria específica definida pela TI.',
    )
    
    equipe = models.ForeignKey(
        'core.Equipe',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tickets',
        help_text='Equipe/Setor de contexto para este chamado.'
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

    co_authors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='coauthored_tickets',
        help_text='Co-autores com acesso e permissão de comentário no chamado.',
    )
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_tickets',
        help_text='Técnico responsável pelo chamado.'
    )
    
    is_rejected = models.BooleanField(default=False, help_text='Indica se o chamado foi recusado pelo técnico.')
    rejection_reason = models.TextField(null=True, blank=True, help_text='Motivo da recusa do chamado.')
    
    unread_by_tech = models.BooleanField(default=False, help_text='Possui interações não lidas pela TI.')
    unread_by_user = models.BooleanField(default=False, help_text='Possui interações não lidas pelo usuário.')
    
    unread_count_tech = models.IntegerField(default=0, help_text='Quantidade de interações não lidas pela TI.')
    unread_count_user = models.IntegerField(default=0, help_text='Quantidade de interações não lidas pelo usuário.')
    
    # Soft delete, arquivamento e timestamps
    is_active = models.BooleanField(default=True, help_text='Indica se o registro está ativo (Soft delete).')
    is_archived = models.BooleanField(default=False, help_text='Indica se o chamado foi arquivado após um tempo resolvido.')
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Momento em que o chamado foi finalizado/resolvido (base do arquivamento automático).',
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_tickets',
        help_text='Usuário que finalizou ou recusou o chamado.',
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text='Data e hora de criação.')
    updated_at = models.DateTimeField(auto_now=True, help_text='Data e hora da última atualização.')

    # Prazos padrão de arquivamento automático (em horas)
    HORAS_ARQUIVAR_RESOLVIDO = 24
    HORAS_ARQUIVAR_RECUSADO = 24

    @classmethod
    def archive_old_tickets(
        cls,
        hours_resolved=None,
        hours_rejected=None,
        days_resolved=None,
        **_kwargs,
    ):
        """
        Arquiva tickets RESOLVED após N horas e REJECTED após M horas.
        Aceita hours_resolved ou days_resolved (legado) para evitar erro em deploy parcial.
        """
        if hours_resolved is None and days_resolved is not None:
            hours_resolved = days_resolved * 24
        if hours_resolved is None:
            hours_resolved = cls.HORAS_ARQUIVAR_RESOLVIDO
        if hours_rejected is None:
            hours_rejected = cls.HORAS_ARQUIVAR_RECUSADO

        now = timezone.now()
        resolved_cutoff = now - timedelta(hours=hours_resolved)

        # Data do último comentário de finalização/recusa (mais confiável que updated_at)
        finalize_subquery = Comment.objects.filter(
            ticket_id=OuterRef('pk'),
            is_active=True,
        ).filter(
            Q(text__startswith='Chamado finalizado') | Q(text__startswith='Chamado recusado')
        ).order_by('-created_at').values('created_at')[:1]

        elegiveis = (
            cls.objects.filter(status=cls.StatusChoices.RESOLVED, is_archived=False)
            .annotate(
                data_comentario_final=Subquery(finalize_subquery, output_field=DateTimeField()),
            )
            .annotate(
                referencia=Case(
                    When(
                        resolved_at__isnull=False,
                        data_comentario_final__isnull=False,
                        then=Least('resolved_at', 'data_comentario_final'),
                    ),
                    default=Coalesce('resolved_at', 'data_comentario_final', 'updated_at'),
                    output_field=DateTimeField(),
                ),
            )
            .filter(referencia__lt=resolved_cutoff)
        )

        pks_arquivar = []
        for ticket in elegiveis.iterator():
            pks_arquivar.append(ticket.pk)
            if not ticket.data_comentario_final:
                continue
            if ticket.resolved_at is None or ticket.resolved_at > ticket.data_comentario_final:
                cls.objects.filter(pk=ticket.pk).update(resolved_at=ticket.data_comentario_final)

        if pks_arquivar:
            cls.objects.filter(pk__in=pks_arquivar).update(is_archived=True)

    def save(self, *args, **kwargs):
        if self.pk:
            try:
                old_status = Ticket.objects.only('status').get(pk=self.pk).status
                if old_status != self.status:
                    self.is_archived = False
                    if self.status == self.StatusChoices.RESOLVED:
                        self.resolved_at = timezone.now()
                    elif old_status == self.StatusChoices.RESOLVED:
                        self.resolved_at = None
                        self.resolved_by = None
            except Ticket.DoesNotExist:
                pass
        elif self.status == self.StatusChoices.RESOLVED:
            self.resolved_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"[{self.get_status_display()}] {self.title} - {self.requester_name}"


import os
import uuid
from django.core.exceptions import ValidationError

def validate_image_attachment(value):
    ext = os.path.splitext(value.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    if ext not in valid_extensions:
        raise ValidationError('Apenas imagens (JPEG, PNG, WEBP) são permitidas.')
    if value.size > 5 * 1024 * 1024:
        raise ValidationError('O arquivo não pode ser maior que 5MB.')

def attachment_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    return os.path.join('ticket_attachments', new_filename)

class TicketAttachment(models.Model):
    """Anexos de imagens para os chamados."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='attachments')
    file_name = models.CharField(max_length=255, help_text='Nome original do arquivo.')
    file = models.FileField(upload_to=attachment_upload_path, validators=[validate_image_attachment])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Anexo do chamado #{self.ticket.id}: {self.file_name}"


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
    attachment = models.FileField(
        upload_to=attachment_upload_path, 
        validators=[validate_image_attachment], 
        null=True, 
        blank=True, 
        help_text='Imagem anexada ao comentário.'
    )
    
    # Soft delete e timestamps
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Comentário de {self.author} em {self.ticket.title}"


class TicketContestation(models.Model):
    """Registro de contestação de chamado finalizado pelo solicitante."""
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='contestations',
        help_text='Chamado contestado.',
    )
    contested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ticket_contestations',
        help_text='Usuário que contestou a finalização.',
    )
    reason = models.TextField(help_text='Motivo informado na contestação.')
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contested_finalizations',
        help_text='Usuário que havia finalizado ou recusado o chamado.',
    )
    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Momento em que o chamado havia sido finalizado.',
    )
    was_rejected = models.BooleanField(
        default=False,
        help_text='Indica se a finalização contestada era uma recusa.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'contestação de chamado'
        verbose_name_plural = 'contestações de chamado'

    def __str__(self) -> str:
        return f'Contestação #{self.pk} — chamado #{self.ticket_id}'
