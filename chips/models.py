from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Operator(models.Model):
    """Cadastro de Operadoras (RF06, RF07)"""
    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Ativa'
        INACTIVE = 'INACTIVE', 'Inativa'

    name = models.CharField(max_length=100, unique=True, help_text="Nome da operadora (Ex: Claro, Vivo)")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)

    def __str__(self):
        return self.name


class Batch(models.Model):
    """Cadastro de Lotes / Envelopes físicos na TI (RF06, RF07)"""
    class StatusChoices(models.TextChoices):
        OPEN = 'OPEN', 'Aberto'
        CLOSED = 'CLOSED', 'Fechado'

    class TipoChoices(models.TextChoices):
        LOTE = 'LOTE', 'Lote'
        ENVELOPE = 'ENVELOPE', 'Envelope'

    identifier = models.CharField(max_length=100, unique=True, help_text="Identificador do Lote/Saquinho")
    tipo = models.CharField(
        max_length=20,
        choices=TipoChoices.choices,
        default=TipoChoices.ENVELOPE,
        help_text='Lote de recebimento ou envelope físico na TI.',
    )
    nome = models.CharField(max_length=150, blank=True, help_text='Nome escrito no envelope.')
    setor = models.CharField(max_length=100, blank=True, help_text='Setor escrito no envelope.')
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.OPEN)
    received_at = models.DateField(auto_now_add=True)

    def __str__(self):
        if self.tipo == self.TipoChoices.ENVELOPE and self.nome:
            return f"Envelope {self.nome}"
        return f"Lote {self.identifier}"

    @property
    def label(self):
        """Rótulo para selects no grid."""
        partes = [self.identifier]
        if self.nome:
            partes.append(self.nome)
        if self.setor:
            partes.append(f"({self.setor})")
        return ' — '.join(partes)


class Chip(models.Model):
    """Cadastro Central de Chips (RF05, RF07)"""
    class StatusChoices(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Disponível'
        IN_USE = 'IN_USE', 'Em Uso'
        BLOCKED = 'BLOCKED', 'Bloqueado'
        CANCELED = 'CANCELED', 'Cancelado'
        LOST = 'LOST', 'Perdido'

    class TechChoices(models.TextChoices):
        PHYSICAL = 'PHYSICAL', 'Físico'
        ESIM = 'ESIM', 'eSIM'

    class PlanChoices(models.TextChoices):
        PREPAID = 'PREPAID', 'Pré-pago'
        POSTPAID = 'POSTPAID', 'Pós-pago'
        CONTROL = 'CONTROL', 'Controle'

    class CustodyChoices(models.TextChoices):
        WITH_TI = 'WITH_TI', 'Na TI'
        WITH_PERSON = 'WITH_PERSON', 'Com pessoa'

    line_number = models.CharField(max_length=20, unique=True, help_text="Número da Linha com DDD")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.AVAILABLE)
    custody = models.CharField(
        max_length=20,
        choices=CustodyChoices.choices,
        default=CustodyChoices.WITH_TI,
        help_text='Onde o chip está fisicamente agora.',
    )
    technology = models.CharField(max_length=20, choices=TechChoices.choices, default=TechChoices.PHYSICAL)
    fixed_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Custo Fixo do Plano")
    iccid = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="ICCID (Número de série do chip)")
    plan_type = models.CharField(max_length=20, choices=PlanChoices.choices, default=PlanChoices.CONTROL)
    activated_at = models.DateField(
        null=True,
        blank=True,
        help_text='Data de ativação no callcenter (primeira entrega).',
    )
    last_blocked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Data do último bloqueio da linha.',
    )

    operator = models.ForeignKey(Operator, on_delete=models.PROTECT, related_name='chips')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='chips')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.line_number} - {self.operator.name}"

    def clean(self):
        if self.custody == self.CustodyChoices.WITH_TI:
            if self.status not in (self.StatusChoices.AVAILABLE, self.StatusChoices.BLOCKED):
                raise ValidationError({'status': 'Chip na TI deve estar Disponível ou Bloqueado.'})
            if not self.batch_id:
                raise ValidationError({'batch': 'Informe o envelope quando o chip estiver na TI.'})
        elif self.custody == self.CustodyChoices.WITH_PERSON:
            if self.status != self.StatusChoices.IN_USE:
                raise ValidationError({'status': 'Chip com pessoa deve estar Em Uso.'})

    def save(self, *args, **kwargs):
        # Sincroniza status com custódia quando não bloqueado/cancelado/perdido
        if self.custody == self.CustodyChoices.WITH_TI and self.status == self.StatusChoices.IN_USE:
            self.status = self.StatusChoices.AVAILABLE
        elif self.custody == self.CustodyChoices.WITH_PERSON:
            self.status = self.StatusChoices.IN_USE
            self.batch = None
        super().save(*args, **kwargs)


class ChipMovement(models.Model):
    """Log de movimentações: Entregas, Devoluções e Transferências (RF03, RF11, RF12, RF13)"""
    class ActionChoices(models.TextChoices):
        DELIVERY = 'DELIVERY', 'Entrega'
        RETURN = 'RETURN', 'Devolução'
        TRANSFER = 'TRANSFER', 'Transferência'

    chip = models.ForeignKey(Chip, on_delete=models.CASCADE, related_name='movements')
    employee_name = models.CharField(max_length=150, help_text="Nome do funcionário que recebeu/devolveu")
    employee_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chip_movements',
        help_text='Usuário do sistema vinculado ao titular.',
    )
    action = models.CharField(max_length=20, choices=ActionChoices.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='chip_movements_registered')

    def __str__(self):
        return f"{self.get_action_display()} - {self.chip.line_number} ({self.employee_name})"


class Recharge(models.Model):
    """Log financeiro e histórico de recargas (RF14)"""
    chip = models.ForeignKey(Chip, on_delete=models.CASCADE, related_name='recharges')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    timestamp = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Recarga R$ {self.amount} em {self.chip.line_number}"
