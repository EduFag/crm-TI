from django.conf import settings
from django.db import models

from integracoes.crypto import decrypt_credentials, encrypt_credentials, mascarar_token


class IntegracaoIA(models.Model):
    """Credencial de provedor de IA cadastrada no sistema."""

    class Provider(models.TextChoices):
        DEEPSEEK = 'deepseek', 'DeepSeek'
        CHATGPT = 'chatgpt', 'ChatGPT'
        GEMINI = 'gemini', 'Gemini'
        GROK = 'grok', 'Grok'
        CLAUDE = 'claude', 'Claude'
        NANO_BANANA = 'nano_banana', 'Nano Banana'

    name = models.CharField(max_length=120, help_text='Nome amigável da integração.')
    provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        help_text='Provedor de IA.',
    )
    credentials_encrypted = models.TextField(
        help_text='Credenciais JSON criptografadas (Fernet).',
    )
    token_hint = models.CharField(
        max_length=8,
        blank=True,
        default='',
        help_text='Últimos caracteres da API key para exibição mascarada.',
    )
    is_active = models.BooleanField(default=True, help_text='Integração ativa.')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='integracoes_ia_criadas',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'integração IA'
        verbose_name_plural = 'integrações IA'

    def __str__(self) -> str:
        return f'{self.name} ({self.get_provider_display()})'

    def set_credentials(self, data: dict) -> None:
        """Criptografa credenciais e atualiza token_hint a partir de api_key."""
        api_key = (data.get('api_key') or '').strip()
        if api_key:
            self.token_hint = api_key[-4:] if len(api_key) >= 4 else api_key
        self.credentials_encrypted = encrypt_credentials(data)

    def get_credentials(self) -> dict:
        return decrypt_credentials(self.credentials_encrypted)

    @property
    def token_mascarado(self) -> str:
        return mascarar_token(self.token_hint)


class IntegracaoApi(models.Model):
    """Credencial de API externa (ex.: MoneyConsig B2B) cadastrada no sistema."""

    class Provider(models.TextChoices):
        MONEYCONSIG = 'moneyconsig', 'MoneyConsig'

    name = models.CharField(max_length=120, help_text='Nome amigável da integração.')
    provider = models.CharField(
        max_length=32,
        choices=Provider.choices,
        help_text='Provedor da API externa.',
    )
    credentials_encrypted = models.TextField(
        help_text='Credenciais JSON criptografadas (Fernet).',
    )
    token_hint = models.CharField(
        max_length=8,
        blank=True,
        default='',
        help_text='Últimos caracteres do token para exibição mascarada.',
    )
    is_active = models.BooleanField(default=True, help_text='Integração ativa.')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='integracoes_api_criadas',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'integração API'
        verbose_name_plural = 'integrações API'

    def __str__(self) -> str:
        return f'{self.name} ({self.get_provider_display()})'

    def set_credentials(self, data: dict) -> None:
        """Criptografa credenciais e atualiza token_hint a partir de api_token."""
        api_token = (data.get('api_token') or '').strip()
        if api_token:
            self.token_hint = api_token[-4:] if len(api_token) >= 4 else api_token
        self.credentials_encrypted = encrypt_credentials(data)

    def get_credentials(self) -> dict:
        return decrypt_credentials(self.credentials_encrypted)

    @property
    def token_mascarado(self) -> str:
        return mascarar_token(self.token_hint)


class AssistenteConfig(models.Model):
    """Configuração singleton do Assistente no Helpdesk (pk=1)."""

    ativo = models.BooleanField(
        default=False,
        help_text='Quando ativo, o Assistente responde chamados de não-TI.',
    )
    integracao = models.ForeignKey(
        IntegracaoIA,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configs_assistente',
        help_text='Integração IA preferencial (senão usa a primeira ativa).',
    )
    integracao_visao = models.ForeignKey(
        IntegracaoIA,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configs_assistente_visao',
        help_text=(
            'Integração multimodal para ler prints (ChatGPT/Gemini). '
            'DeepSeek não lê imagem — use outro provedor aqui.'
        ),
    )
    atualizado_em = models.DateTimeField(auto_now=True)
    ultima_geracao_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Última geração de chunks de aprendizado.',
    )

    class Meta:
        verbose_name = 'configuração do assistente'
        verbose_name_plural = 'configuração do assistente'

    def __str__(self) -> str:
        return f'Assistente ({"ativo" if self.ativo else "inativo"})'

    @classmethod
    def get_solo(cls) -> 'AssistenteConfig':
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'ativo': False})
        return obj


class AssistenteChunk(models.Model):
    """Trecho de aprendizado gerado a partir de chamados finalizados."""

    class Origem(models.TextChoices):
        IA = 'ia', 'Gerado pela IA'
        MANUAL = 'manual', 'Manual'
        CHAT = 'chat', 'Chat de memória'

    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    categoria_hint = models.CharField(max_length=120, blank=True, default='')
    fonte_ticket_ids = models.JSONField(default=list, blank=True)
    # Existentes preservados como manual para não serem apagados na regeneração
    origem = models.CharField(
        max_length=16,
        choices=Origem.choices,
        default=Origem.MANUAL,
        help_text='Como o chunk foi criado (ia/manual/chat).',
    )
    ativo = models.BooleanField(
        default=True,
        help_text='Se falso, o chunk não entra no contexto do Assistente.',
    )
    tags = models.JSONField(default=list, blank=True)
    # Vetor para retrieval híbrido (JSON — compatível SQLite/Postgres)
    embedding = models.JSONField(
        null=True,
        blank=True,
        help_text='Lista de floats do embedding; null se ainda não calculado.',
    )
    embedding_modelo = models.CharField(
        max_length=80,
        blank=True,
        default='',
        help_text='Modelo usado no último embedding (ex.: text-embedding-3-small).',
    )
    embedding_em = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Quando o embedding foi gerado.',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-atualizado_em', '-criado_em']
        verbose_name = 'chunk de aprendizado'
        verbose_name_plural = 'chunks de aprendizado'

    def __str__(self) -> str:
        return self.titulo


class AssistenteInteracao(models.Model):
    """Rodada do Assistente com os chunks usados (para eval / feedback da TI)."""

    class Nota(models.IntegerChoices):
        UTIL = 1, 'Útil'
        RUIM = -1, 'Ruim'

    ticket_id = models.PositiveIntegerField(db_index=True)
    chunk_ids = models.JSONField(default=list, blank=True)
    informative_ids = models.JSONField(
        default=list,
        blank=True,
        help_text='IDs de InformativeMessage usados nesta rodada.',
    )
    hybrid = models.BooleanField(
        default=False,
        help_text='True se a query usou embedding semântico nesta rodada.',
    )
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    nota = models.SmallIntegerField(
        null=True,
        blank=True,
        choices=Nota.choices,
        help_text='null = sem avaliação; 1 = útil; -1 = ruim.',
    )
    nota_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='avaliacoes_assistente',
    )
    nota_em = models.DateTimeField(null=True, blank=True)
    comentario = models.CharField(max_length=400, blank=True, default='')

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'interação do assistente'
        verbose_name_plural = 'interações do assistente'

    def __str__(self) -> str:
        return f'Interação ticket #{self.ticket_id} @ {self.criado_em}'


class AssistenteMemoriaConversa(models.Model):
    """Thread persistente do chat de memória na página de Aprendizado."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversas_memoria_assistente',
    )
    titulo = models.CharField(max_length=160, blank=True, default='Nova conversa')
    mensagens = models.JSONField(
        default=list,
        blank=True,
        help_text='Lista de {role, content} (user/assistant).',
    )
    ativo = models.BooleanField(
        default=True,
        help_text='False = arquivada (some do histórico ativo).',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-atualizado_em']
        verbose_name = 'conversa de memória'
        verbose_name_plural = 'conversas de memória'

    def __str__(self) -> str:
        return f'{self.titulo} (#{self.pk})'


class TokenApiExterna(models.Model):
    """Token de API para integração do CRM-TI com sistemas externos do usuário."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tokens_api_externa',
        help_text='Usuário dono do token.',
    )
    nome = models.CharField(
        max_length=120,
        help_text='Rótulo amigável (ex.: sistema do cliente).',
    )
    prefixo = models.CharField(
        max_length=12,
        help_text='Primeiros caracteres do token para identificação na UI.',
    )
    token_hash = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text='SHA-256 do token em texto claro.',
    )
    ativo = models.BooleanField(default=True, help_text='False = revogado.')
    criado_em = models.DateTimeField(auto_now_add=True)
    ultimo_uso = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Última autenticação ou chamada autenticada.',
    )

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'token API externa'
        verbose_name_plural = 'tokens API externa'

    def __str__(self) -> str:
        return f'{self.nome} ({self.prefixo}…) — {self.user}'

    @property
    def token_mascarado(self) -> str:
        return f'{self.prefixo}…'
