from django.db import models
from django.conf import settings

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
    """Cadastro de Lotes / Saquinhos (RF06, RF07)"""
    class StatusChoices(models.TextChoices):
        OPEN = 'OPEN', 'Aberto'
        CLOSED = 'CLOSED', 'Fechado'
        
    identifier = models.CharField(max_length=100, unique=True, help_text="Identificador do Lote/Saquinho")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.OPEN)
    received_at = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"Lote {self.identifier}"

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

    line_number = models.CharField(max_length=20, unique=True, help_text="Número da Linha com DDD")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.AVAILABLE)
    technology = models.CharField(max_length=20, choices=TechChoices.choices, default=TechChoices.PHYSICAL)
    fixed_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Custo Fixo do Plano")
    iccid = models.CharField(max_length=50, unique=True, blank=True, null=True, help_text="ICCID (Número de série do chip)")
    plan_type = models.CharField(max_length=20, choices=PlanChoices.choices, default=PlanChoices.CONTROL)
    
    operator = models.ForeignKey(Operator, on_delete=models.PROTECT, related_name='chips')
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='chips')
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.line_number} - {self.operator.name}"

class ChipMovement(models.Model):
    """Log de movimentações: Entregas e Devoluções (RF03, RF11, RF12, RF13)"""
    class ActionChoices(models.TextChoices):
        DELIVERY = 'DELIVERY', 'Entrega'
        RETURN = 'RETURN', 'Devolução'
        
    chip = models.ForeignKey(Chip, on_delete=models.CASCADE, related_name='movements')
    employee_name = models.CharField(max_length=150, help_text="Nome do funcionário que recebeu/devolveu")
    action = models.CharField(max_length=20, choices=ActionChoices.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

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
