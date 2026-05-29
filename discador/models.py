from django.db import models
from django.conf import settings

class ConfiguracaoAPI(models.Model):
    """Configurações de integração com a API da 3C Plus."""
    nome = models.CharField(max_length=100)
    base_url = models.URLField(max_length=255)
    api_token = models.CharField(max_length=255)
    campaign_ids = models.CharField(max_length=255, help_text="IDs separados por vírgula")
    per_page = models.IntegerField(default=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome

class LigacaoImportada(models.Model):
    """Ligações retornadas pela API."""
    call_id = models.CharField(max_length=100, unique=True)
    telefone_original = models.CharField(max_length=30)
    telefone_normalizado = models.CharField(max_length=20)
    campanha_id = models.CharField(max_length=100)
    campanha_nome = models.CharField(max_length=150)
    agente_nome = models.CharField(max_length=150, null=True, blank=True)
    status = models.CharField(max_length=100)
    qualificacao = models.CharField(max_length=100)
    observacao = models.TextField(null=True, blank=True)
    data_ligacao = models.DateTimeField()
    payload_original = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.telefone_normalizado} - {self.qualificacao}"

class RegraReciclagem(models.Model):
    """Regras para bloquear ou ignorar qualificações."""
    ACAO_CHOICES = (
        ('bloquear', 'Bloquear'),
        ('ignorar', 'Ignorar'),
        ('monitorar', 'Monitorar'),
    )
    TIPO_BLOQUEIO_CHOICES = (
        ('temporario', 'Temporário'),
        ('permanente', 'Permanente'),
    )

    qualificacao = models.CharField(max_length=100)
    acao = models.CharField(max_length=20, choices=ACAO_CHOICES)
    tipo_bloqueio = models.CharField(max_length=20, choices=TIPO_BLOQUEIO_CHOICES, null=True, blank=True)
    dias_bloqueio = models.IntegerField(default=0, help_text="Se temporário, quantos dias bloquear?")
    aplicar_por_telefone = models.BooleanField(default=True)
    aplicar_por_cpf = models.BooleanField(default=False)
    campanha_id = models.CharField(max_length=100, null=True, blank=True, help_text="Deixe em branco para todas")
    prioridade = models.IntegerField(default=1, help_text="Maior número = maior prioridade")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.qualificacao} -> {self.acao}"

class Blacklist(models.Model):
    """Contatos bloqueados."""
    ORIGEM_CHOICES = (
        ('api', 'API'),
        ('csv', 'CSV'),
        ('manual', 'Manual'),
    )
    telefone_original = models.CharField(max_length=30)
    telefone_normalizado = models.CharField(max_length=20, db_index=True)
    cpf = models.CharField(max_length=20, null=True, blank=True, db_index=True)
    qualificacao_origem = models.CharField(max_length=100)
    campanha_id = models.CharField(max_length=100, null=True, blank=True)
    campanha_nome = models.CharField(max_length=150, null=True, blank=True)
    call_id = models.CharField(max_length=100, null=True, blank=True)
    data_ligacao = models.DateTimeField(null=True, blank=True)
    tipo_bloqueio = models.CharField(max_length=20)
    bloqueado_em = models.DateTimeField()
    bloqueado_ate = models.DateTimeField(null=True, blank=True)
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default='api')
    is_active = models.BooleanField(default=True)
    payload_original = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.telefone_normalizado

class ImportacaoAPI(models.Model):
    """Histórico de importações da API."""
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField(null=True, blank=True)
    periodo_inicial = models.DateTimeField()
    periodo_final = models.DateTimeField()
    campanhas = models.CharField(max_length=255)
    total_ligacoes = models.IntegerField(default=0)
    total_com_qualificacao = models.IntegerField(default=0)
    total_bloqueios = models.IntegerField(default=0)
    total_ignorados = models.IntegerField(default=0)
    total_erros = models.IntegerField(default=0)
    status = models.CharField(max_length=50)
    log = models.TextField(null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Importação {self.id} - {self.status}"

class ProcessamentoBase(models.Model):
    """Processamento de bases CSV para discador."""
    nome = models.CharField(max_length=150)
    campanha_destino = models.CharField(max_length=150)
    arquivo_original = models.FileField(upload_to='discador/originais/')
    arquivo_reciclado = models.FileField(upload_to='discador/reciclados/', null=True, blank=True)
    arquivo_bloqueados = models.FileField(upload_to='discador/bloqueados/', null=True, blank=True)
    coluna_telefone = models.CharField(max_length=100)
    coluna_cpf = models.CharField(max_length=100, null=True, blank=True)
    total_linhas = models.IntegerField(default=0)
    total_liberadas = models.IntegerField(default=0)
    total_bloqueadas = models.IntegerField(default=0)
    total_duplicadas = models.IntegerField(default=0)
    total_erros = models.IntegerField(default=0)
    status = models.CharField(max_length=50)
    log = models.TextField(null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finalizado_em = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.nome} - {self.status}"
