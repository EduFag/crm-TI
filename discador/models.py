from django.conf import settings
from django.db import models


class Discador(models.Model):
    """Provedor de discador (ex.: JoyTec) com contrato de licenças."""

    nome = models.CharField(max_length=100, help_text='Nome do provedor de discador.')
    slug = models.SlugField(max_length=50, unique=True, help_text='Identificador único na URL.')
    valor_por_licenca = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Valor cobrado por licença ativa.',
    )
    licencas_contratadas = models.PositiveIntegerField(
        default=0,
        help_text='Quantidade de licenças contratadas no momento.',
    )
    is_active = models.BooleanField(default=True, help_text='Discador ativo no sistema.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Discador'
        verbose_name_plural = 'Discadores'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def custo_mensal(self):
        return self.valor_por_licenca * self.licencas_contratadas


class DiscadorContratoHistorico(models.Model):
    """Snapshot append-only de alterações no contrato de licenças."""

    discador = models.ForeignKey(
        Discador,
        on_delete=models.CASCADE,
        related_name='historico_contrato',
    )
    valor_por_licenca = models.DecimalField(max_digits=10, decimal_places=2)
    licencas_contratadas = models.PositiveIntegerField()
    observacao = models.CharField(max_length=255, blank=True, default='')
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discador_contrato_logs',
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico de contrato'
        verbose_name_plural = 'Históricos de contrato'
        ordering = ['-timestamp']

    def __str__(self):
        return (
            f'{self.discador.nome}: {self.licencas_contratadas} lic. '
            f'@ {self.valor_por_licenca} ({self.timestamp:%d/%m/%Y %H:%M})'
        )


class Campanha(models.Model):
    """Campanha vinculada a um discador."""

    discador = models.ForeignKey(
        Discador,
        on_delete=models.CASCADE,
        related_name='campanhas',
    )
    nome = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True, help_text='Campanha disponível para novos acessos.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Campanha'
        verbose_name_plural = 'Campanhas'
        ordering = ['nome']
        unique_together = [('discador', 'nome')]

    def __str__(self):
        return self.nome


class Ramal(models.Model):
    """Ramal do discador — consome licença quando Em uso ou Livre."""

    class StatusChoices(models.TextChoices):
        IN_USE = 'IN_USE', 'Ramal em uso'
        FREE = 'FREE', 'Livre'
        NOT_CONFIGURED = 'NOT_CONFIGURED', 'Não configurado'

    discador = models.ForeignKey(
        Discador,
        on_delete=models.CASCADE,
        related_name='ramais',
    )
    numero = models.CharField(max_length=50, help_text='Número do ramal no discador.')
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.NOT_CONFIGURED,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Ramal'
        verbose_name_plural = 'Ramais'
        ordering = ['numero']
        unique_together = [('discador', 'numero')]

    def __str__(self):
        return self.numero

    @property
    def consome_licenca(self):
        return self.status in (
            self.StatusChoices.IN_USE,
            self.StatusChoices.FREE,
        )


class AcessoDiscador(models.Model):
    """Acesso atual de um titular a um ramal/login no discador."""

    class TipoChoices(models.TextChoices):
        CONSULTOR = 'CONSULTOR', 'Consultor(a)'
        VENDEDOR = 'VENDEDOR', 'Vendedor(a)'
        NEGOCIADOR = 'NEGOCIADOR', 'Negociador(a)'

    discador = models.ForeignKey(
        Discador,
        on_delete=models.CASCADE,
        related_name='acessos',
    )
    titular_nome = models.CharField(
        max_length=150,
        blank=True,
        default='',
        help_text='Nome do titular (snapshot).',
    )
    titular_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acessos_discador',
        help_text='Usuário do sistema, se houver.',
    )
    login_discador = models.CharField(max_length=100, help_text='Login no discador.')
    ramal = models.OneToOneField(
        Ramal,
        on_delete=models.PROTECT,
        related_name='acesso',
        help_text='Ramal associado a este acesso.',
    )
    campanha = models.ForeignKey(
        Campanha,
        on_delete=models.PROTECT,
        related_name='acessos',
    )
    tipo = models.CharField(max_length=20, choices=TipoChoices.choices)
    status = models.CharField(
        max_length=20,
        choices=Ramal.StatusChoices.choices,
        default=Ramal.StatusChoices.IN_USE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Acesso do discador'
        verbose_name_plural = 'Acessos do discador'
        ordering = ['titular_nome', 'login_discador']

    def __str__(self):
        nome = self.titular_nome or self.login_discador
        return f'{nome} — {self.ramal.numero}'

    @property
    def nome_exibicao(self):
        if self.titular_user_id:
            return self.titular_user.get_full_name() or self.titular_user.username
        return self.titular_nome or '—'


class RamalAtribuicaoHistorico(models.Model):
    """Histórico append-only de quem usou cada ramal."""

    class ActionChoices(models.TextChoices):
        ASSIGNED = 'ASSIGNED', 'Atribuição'
        TRANSFERRED = 'TRANSFERRED', 'Transferência'
        FREED = 'FREED', 'Liberado'
        DELETED = 'DELETED', 'Exclusão do acesso'
        STATUS_CHANGED = 'STATUS_CHANGED', 'Mudança de status'
        CREATED = 'CREATED', 'Cadastro do ramal'

    ramal = models.ForeignKey(
        Ramal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historico_atribuicoes',
    )
    discador = models.ForeignKey(
        Discador,
        on_delete=models.CASCADE,
        related_name='historico_atribuicoes',
        null=True,
        blank=True,
    )
    ramal_numero = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text='Snapshot do número do ramal (preserva histórico se o ramal for excluído).',
    )
    action = models.CharField(max_length=20, choices=ActionChoices.choices)
    titular_nome = models.CharField(max_length=150, blank=True, default='')
    login_discador = models.CharField(max_length=100, blank=True, default='')
    campanha_nome = models.CharField(max_length=150, blank=True, default='')
    tipo = models.CharField(max_length=20, blank=True, default='')
    status = models.CharField(max_length=20, blank=True, default='')
    observacao = models.CharField(max_length=255, blank=True, default='')
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='discador_atribuicao_logs',
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico de atribuição de ramal'
        verbose_name_plural = 'Históricos de atribuição de ramal'
        ordering = ['-timestamp']

    def __str__(self):
        numero = self.ramal_numero or (self.ramal.numero if self.ramal_id else '?')
        return f'{numero} — {self.get_action_display()} ({self.timestamp:%d/%m/%Y %H:%M})'
