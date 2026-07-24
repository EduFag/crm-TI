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

    titulo = models.CharField(max_length=200)
    conteudo = models.TextField()
    categoria_hint = models.CharField(max_length=120, blank=True, default='')
    fonte_ticket_ids = models.JSONField(default=list, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'chunk de aprendizado'
        verbose_name_plural = 'chunks de aprendizado'

    def __str__(self) -> str:
        return self.titulo
