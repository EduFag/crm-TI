from django.db import models
from django.utils import timezone

class Equipment(models.Model):
    """ RF04: Modelo de Cadastro de Ativos e Ciclo de Vida """
    class EquipmentType(models.TextChoices):
        NOTEBOOK = 'NOTEBOOK', 'Notebook'
        DESKTOP = 'DESKTOP', 'Desktop'
        MONITOR = 'MONITOR', 'Monitor'
        SMARTPHONE = 'SMARTPHONE', 'Smartphone'
        PERIPHERAL = 'PERIPHERAL', 'Periférico'
        OTHER = 'OTHER', 'Outro'

    class StatusChoices(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Disponível'
        IN_USE = 'IN_USE', 'Em Uso'
        MAINTENANCE = 'MAINTENANCE', 'Em Manutenção'
        SCRAP = 'SCRAP', 'Sucata/Descartado'

    # Informações Base
    type = models.CharField(max_length=20, choices=EquipmentType.choices, default=EquipmentType.NOTEBOOK)
    tag = models.CharField(max_length=100, unique=True, help_text="Código de Patrimônio (Tag)")
    serial_number = models.CharField(max_length=150, unique=True, help_text="Número de Série")
    brand_model = models.CharField(max_length=200, help_text="Marca / Modelo")
    
    # Informações Financeiras e Garantia
    purchase_date = models.DateField(help_text="Data de Compra")
    warranty_end = models.DateField(help_text="Data Fim da Garantia")
    purchase_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor de Compra")
    
    # RF05: Ciclo de Vida
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.AVAILABLE)
    current_employee = models.CharField(max_length=200, blank=True, null=True, help_text="Funcionário Atual")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_warranty_expired(self):
        """ Retorna verdadeiro se a garantia já expirou baseado no momento atual """
        return timezone.now().date() > self.warranty_end

    def __str__(self):
        return f"[{self.tag}] {self.brand_model}"

class EquipmentLog(models.Model):
    """ RF02: Histórico de Movimentações (Log Intocável) """
    class ActionChoices(models.TextChoices):
        ASSIGNED = 'ASSIGNED', 'Atribuição'
        RETURNED = 'RETURNED', 'Devolução'
        MAINTENANCE = 'MAINTENANCE', 'Enviado para Manutenção'
        SCRAPPED = 'SCRAPPED', 'Descartado/Sucateado'
        CREATED = 'CREATED', 'Cadastro Inicial'

    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=20, choices=ActionChoices.choices)
    employee_name = models.CharField(max_length=200, blank=True, null=True, help_text="Funcionário Envolvido")
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.equipment.tag} - {self.action}"
