"""Configuração de provedores e campos do wizard de integração IA."""

from integracoes.models import IntegracaoIA

# Campos que nunca vão em credentials_encrypted (ficam no model)
CAMPOS_META = frozenset({'name', 'provider', 'is_active'})

# Definição dos campos por provedor (página 2 do modal)
PROVIDER_FIELDS = {
    IntegracaoIA.Provider.DEEPSEEK: [
        {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: DeepSeek produção'},
        {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'sk-...'},
        {
            'name': 'base_url',
            'label': 'Base URL',
            'type': 'url',
            'required': False,
            'default': 'https://api.deepseek.com',
            'placeholder': 'https://api.deepseek.com',
        },
        {
            'name': 'model',
            'label': 'Modelo',
            'type': 'text',
            'required': False,
            'default': 'deepseek-chat',
            'placeholder': 'deepseek-chat',
        },
    ],
    IntegracaoIA.Provider.CHATGPT: [
        {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: OpenAI suporte'},
        {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'sk-...'},
        {
            'name': 'organization_id',
            'label': 'Organization ID',
            'type': 'text',
            'required': False,
            'placeholder': 'org-... (opcional)',
        },
        {
            'name': 'model',
            'label': 'Modelo',
            'type': 'text',
            'required': False,
            'default': 'gpt-4o-mini',
            'placeholder': 'gpt-4o-mini',
        },
    ],
    IntegracaoIA.Provider.GEMINI: [
        {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: Gemini operação'},
        {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'AIza...'},
        {
            'name': 'model',
            'label': 'Modelo',
            'type': 'text',
            'required': False,
            'default': 'gemini-2.0-flash',
            'placeholder': 'gemini-2.0-flash',
        },
    ],
    IntegracaoIA.Provider.GROK: [
        {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: Grok xAI'},
        {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'xai-...'},
        {
            'name': 'model',
            'label': 'Modelo',
            'type': 'text',
            'required': False,
            'default': 'grok-2-latest',
            'placeholder': 'grok-2-latest',
        },
    ],
    IntegracaoIA.Provider.CLAUDE: [
        {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: Claude Anthropic'},
        {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'sk-ant-...'},
        {
            'name': 'model',
            'label': 'Modelo',
            'type': 'text',
            'required': False,
            'default': 'claude-sonnet-4-20250514',
            'placeholder': 'claude-sonnet-4-20250514',
        },
    ],
    IntegracaoIA.Provider.NANO_BANANA: [
        {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: Nano Banana imagens'},
        {
            'name': 'api_key',
            'label': 'API Key (Google AI)',
            'type': 'password',
            'required': True,
            'sensitive': True,
            'placeholder': 'AIza...',
        },
        {
            'name': 'model',
            'label': 'Modelo',
            'type': 'text',
            'required': False,
            'default': 'gemini-2.0-flash-preview-image-generation',
            'placeholder': 'modelo Google AI',
        },
    ],
}

PROVIDER_META = {
    IntegracaoIA.Provider.DEEPSEEK: {
        'label': 'DeepSeek',
        'descricao': 'Modelos DeepSeek Chat / Reasoner',
        'accent': 'slate',
    },
    IntegracaoIA.Provider.CHATGPT: {
        'label': 'ChatGPT',
        'descricao': 'OpenAI GPT (Chat Completions)',
        'accent': 'emerald',
    },
    IntegracaoIA.Provider.GEMINI: {
        'label': 'Gemini',
        'descricao': 'Google Gemini API',
        'accent': 'sky',
    },
    IntegracaoIA.Provider.GROK: {
        'label': 'Grok',
        'descricao': 'xAI Grok',
        'accent': 'amber',
    },
    IntegracaoIA.Provider.CLAUDE: {
        'label': 'Claude',
        'descricao': 'Anthropic Claude',
        'accent': 'orange',
    },
    IntegracaoIA.Provider.NANO_BANANA: {
        'label': 'Nano Banana',
        'descricao': 'Google AI — geração de imagem',
        'accent': 'violet',
    },
}


def campos_do_provedor(provider: str) -> list[dict]:
    return list(PROVIDER_FIELDS.get(provider, []))


def lista_provedores() -> list[dict]:
    itens = []
    for codigo, meta in PROVIDER_META.items():
        itens.append({
            'codigo': codigo,
            'label': meta['label'],
            'descricao': meta['descricao'],
            'accent': meta['accent'],
            'fields': campos_do_provedor(codigo),
        })
    return itens
