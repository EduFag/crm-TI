from django.db import models

class EmailDomain(models.Model):
    """Domínios corporativos permitidos para criação de caixas"""
    name = models.CharField(max_length=255, unique=True, help_text="Ex: empresa.com.br")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class EmailAccount(models.Model):
    """Inventário de Contas de E-mail"""
    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Ativa'
        BLOCKED = 'BLOCKED', 'Bloqueada'

    username = models.CharField(max_length=150, help_text="Prefixo (ex: joao.silva)", null=True)
    domain = models.ForeignKey(EmailDomain, on_delete=models.PROTECT, related_name='accounts', null=True)
    
    employee_name = models.CharField(max_length=150, help_text="Nome do funcionário vinculado")
    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    
    # Rastreabilidade
    last_password_reset = models.DateTimeField(null=True, blank=True, help_text="Data do último reset")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('username', 'domain')

    @property
    def address(self):
        if self.username and self.domain:
            return f"{self.username}@{self.domain.name}"
        return "Configuração Incompleta"

    def __str__(self):
        return self.address
