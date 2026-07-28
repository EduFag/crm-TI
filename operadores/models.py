from django.db import models

class Setor(models.Model):
    name = models.CharField("Nome do Setor", max_length=100, unique=True, help_text="Ex: INSS, LOJA, SIAPE")

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ['name']

    def __str__(self):
        return self.name

class Ilha(models.Model):
    name = models.CharField("Nome da Ilha", max_length=100)
    setor = models.ForeignKey('core.Equipe', on_delete=models.PROTECT, related_name="ilhas", verbose_name="Setor / Equipe")

    class Meta:
        verbose_name = "Ilha"
        verbose_name_plural = "Ilhas"
        ordering = ['setor__name', 'name']
        unique_together = ('name', 'setor')

    def __str__(self):
        return f"{self.name} ({self.setor.name})"

class PA(models.Model):
    name = models.CharField("Nome da PA", max_length=100, help_text="Ex: PA 01")
    ilha = models.ForeignKey(Ilha, on_delete=models.PROTECT, related_name="pas", verbose_name="Ilha")

    class Meta:
        verbose_name = "PA"
        verbose_name_plural = "PAs"
        ordering = ['ilha__name', 'name']
        unique_together = ('name', 'ilha')

    def __str__(self):
        return f"{self.name} - {self.ilha.name}"

class Operador(models.Model):
    name = models.CharField("Nome do Operador", max_length=150)
    pa = models.OneToOneField(PA, on_delete=models.SET_NULL, null=True, blank=True, related_name="operador", verbose_name="Posição de Atendimento (PA)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Operador"
        verbose_name_plural = "Operadores"
        ordering = ['name']

    def __str__(self):
        return self.name

class WhatsAppAccount(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Ativa'
        RESTRICTED = 'RESTRICTED', 'Restringido'
        SUSPENDED = 'SUSPENDED', 'Em Análise'
        BANNED = 'BANNED', 'Banido'

    class AccountTypeChoices(models.TextChoices):
        BUSINESS = 'BUSINESS', 'WhatsApp Business'
        STANDARD = 'STANDARD', 'WhatsApp Normal'

    phone_number = models.CharField("Número / Identificador", max_length=50, unique=True, null=True, blank=True, help_text="Número do WhatsApp")
    account_type = models.CharField(
        "Tipo de Conta",
        max_length=20,
        choices=AccountTypeChoices.choices,
        default=AccountTypeChoices.BUSINESS,
        help_text="Defina se a conta é WhatsApp Business ou Normal"
    )
    status = models.CharField("Status da Conta", max_length=20, choices=StatusChoices.choices, default=StatusChoices.ACTIVE)
    
    operador = models.ForeignKey(Operador, on_delete=models.SET_NULL, null=True, blank=True, related_name="whatsapp_accounts", verbose_name="Operador")
    chip = models.OneToOneField('chips.Chip', on_delete=models.SET_NULL, null=True, blank=True, related_name="whatsapp_account", verbose_name="Chip Vinculado")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Conta WhatsApp"
        verbose_name_plural = "Contas WhatsApp"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_account_type_display()} - {self.phone_number or (self.chip.line_number if self.chip else 'Sem linha')}"

    @property
    def last_four_digits(self):
        num = self.phone_number or (self.chip.line_number if self.chip else '')
        clean = ''.join(filter(str.isdigit, num))
        return clean[-4:] if len(clean) >= 4 else (clean or '----')

    @property
    def formatted_number(self):
        if self.chip:
            return self.chip.formatted_line_number
        return self.phone_number or 'Sem linha'

    def save(self, *args, **kwargs):
        if self.chip:
            self.phone_number = self.chip.line_number
        elif not self.phone_number and self.pk:
            old = WhatsAppAccount.objects.filter(pk=self.pk).first()
            if old and old.chip:
                self.phone_number = old.chip.line_number

        if self.pk:
            old_instance = WhatsAppAccount.objects.get(pk=self.pk)
            old_chip = old_instance.chip
        else:
            old_chip = None

        super().save(*args, **kwargs)

        if old_chip and old_chip != self.chip:
            if old_chip.status == old_chip.StatusChoices.ACTIVE:
                old_chip.usage_status = old_chip.UsageChoices.AVAILABLE
            else:
                old_chip.usage_status = old_chip.UsageChoices.UNAVAILABLE
            old_chip.save(update_fields=['usage_status'])

        if self.chip:
            if self.status == self.StatusChoices.BANNED and self.chip.status != self.chip.StatusChoices.BANNED:
                self.chip.status = self.chip.StatusChoices.BANNED
                self.chip.save(update_fields=['status', 'usage_status'])
            else:
                if self.operador:
                    self.chip.usage_status = self.chip.UsageChoices.IN_USE
                else:
                    if self.chip.status == self.chip.StatusChoices.ACTIVE:
                        self.chip.usage_status = self.chip.UsageChoices.AVAILABLE
                    else:
                        self.chip.usage_status = self.chip.UsageChoices.UNAVAILABLE
                self.chip.save(update_fields=['usage_status'])
