"""Configuração de provedores e campos do wizard de integração IA.

URL e catálogo de modelos são definidos pelo sistema.
O usuário só escolhe quais modelos liberar (checklist).
"""

from integracoes.models import IntegracaoIA

# Campos que ficam no model (não no blob de credenciais)
CAMPOS_META = frozenset({'name', 'provider', 'is_active'})

# Catálogo oficial por provedor (URL + modelos suportados pelo sistema)
PROVIDER_CONFIG = {
    IntegracaoIA.Provider.DEEPSEEK: {
        'label': 'DeepSeek',
        'descricao': 'Modelos DeepSeek Chat / Reasoner',
        'accent': 'slate',
        'base_url': 'https://api.deepseek.com',
        'models': [
            {'id': 'deepseek-chat', 'label': 'DeepSeek Chat'},
            {'id': 'deepseek-reasoner', 'label': 'DeepSeek Reasoner'},
        ],
        'default_models': ['deepseek-chat'],
        'fields': [
            {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: DeepSeek produção'},
            {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'sk-...'},
        ],
    },
    IntegracaoIA.Provider.CHATGPT: {
        'label': 'ChatGPT',
        'descricao': 'OpenAI GPT (Chat Completions)',
        'accent': 'emerald',
        'base_url': 'https://api.openai.com/v1',
        'models': [
            {'id': 'gpt-4o-mini', 'label': 'GPT-4o mini'},
            {'id': 'gpt-4o', 'label': 'GPT-4o'},
            {'id': 'gpt-4.1-mini', 'label': 'GPT-4.1 mini'},
            {'id': 'gpt-4.1', 'label': 'GPT-4.1'},
            {'id': 'o4-mini', 'label': 'o4-mini'},
        ],
        'default_models': ['gpt-4o-mini'],
        'fields': [
            {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: OpenAI suporte'},
            {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'sk-...'},
            {
                'name': 'organization_id',
                'label': 'Organization ID',
                'type': 'text',
                'required': False,
                'placeholder': 'org-... (opcional)',
            },
        ],
    },
    IntegracaoIA.Provider.GEMINI: {
        'label': 'Gemini',
        'descricao': 'Google Gemini API',
        'accent': 'sky',
        'base_url': 'https://generativelanguage.googleapis.com/v1beta',
        'models': [
            {'id': 'gemini-2.0-flash', 'label': 'Gemini 2.0 Flash'},
            {'id': 'gemini-2.0-flash-lite', 'label': 'Gemini 2.0 Flash Lite'},
            {'id': 'gemini-1.5-pro', 'label': 'Gemini 1.5 Pro'},
            {'id': 'gemini-1.5-flash', 'label': 'Gemini 1.5 Flash'},
        ],
        'default_models': ['gemini-2.0-flash'],
        'fields': [
            {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: Gemini operação'},
            {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'AIza...'},
        ],
    },
    IntegracaoIA.Provider.GROK: {
        'label': 'Grok',
        'descricao': 'xAI Grok',
        'accent': 'amber',
        'base_url': 'https://api.x.ai/v1',
        'models': [
            {'id': 'grok-2-latest', 'label': 'Grok 2 Latest'},
            {'id': 'grok-2', 'label': 'Grok 2'},
            {'id': 'grok-3-mini', 'label': 'Grok 3 mini'},
        ],
        'default_models': ['grok-2-latest'],
        'fields': [
            {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: Grok xAI'},
            {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'xai-...'},
        ],
    },
    IntegracaoIA.Provider.CLAUDE: {
        'label': 'Claude',
        'descricao': 'Anthropic Claude',
        'accent': 'orange',
        'base_url': 'https://api.anthropic.com',
        'models': [
            {'id': 'claude-sonnet-4-20250514', 'label': 'Claude Sonnet 4'},
            {'id': 'claude-opus-4-20250514', 'label': 'Claude Opus 4'},
            {'id': 'claude-3-5-haiku-20241022', 'label': 'Claude 3.5 Haiku'},
        ],
        'default_models': ['claude-sonnet-4-20250514'],
        'fields': [
            {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: Claude Anthropic'},
            {'name': 'api_key', 'label': 'API Key', 'type': 'password', 'required': True, 'sensitive': True, 'placeholder': 'sk-ant-...'},
        ],
    },
    IntegracaoIA.Provider.NANO_BANANA: {
        'label': 'Nano Banana',
        'descricao': 'Google AI — geração de imagem',
        'accent': 'violet',
        'base_url': 'https://generativelanguage.googleapis.com/v1beta',
        'models': [
            {
                'id': 'gemini-2.0-flash-preview-image-generation',
                'label': 'Gemini 2.0 Flash (imagem)',
            },
            {
                'id': 'imagen-3.0-generate-002',
                'label': 'Imagen 3',
            },
        ],
        'default_models': ['gemini-2.0-flash-preview-image-generation'],
        'fields': [
            {'name': 'name', 'label': 'Nome', 'type': 'text', 'required': True, 'placeholder': 'Ex.: Nano Banana imagens'},
            {
                'name': 'api_key',
                'label': 'API Key (Google AI)',
                'type': 'password',
                'required': True,
                'sensitive': True,
                'placeholder': 'AIza...',
            },
        ],
    },
}


def config_do_provedor(provider: str) -> dict:
    return PROVIDER_CONFIG.get(provider) or {}


def base_url_do_provedor(provider: str) -> str:
    return config_do_provedor(provider).get('base_url', '')


def modelos_do_provedor(provider: str) -> list[dict]:
    return list(config_do_provedor(provider).get('models') or [])


def ids_modelos_permitidos(provider: str) -> set[str]:
    return {m['id'] for m in modelos_do_provedor(provider)}


def modelos_padrao(provider: str) -> list[str]:
    return list(config_do_provedor(provider).get('default_models') or [])


def campos_do_provedor(provider: str) -> list[dict]:
    """Campos preenchíveis pelo usuário (sem URL/modelo livre)."""
    return list(config_do_provedor(provider).get('fields') or [])


def lista_provedores() -> list[dict]:
    itens = []
    for codigo, cfg in PROVIDER_CONFIG.items():
        itens.append({
            'codigo': codigo,
            'label': cfg['label'],
            'descricao': cfg['descricao'],
            'accent': cfg['accent'],
            'base_url': cfg['base_url'],
            'models': cfg['models'],
            'default_models': cfg['default_models'],
            'fields': list(cfg['fields']),
        })
    return itens


def normalizar_modelos_salvos(credenciais: dict) -> list[str]:
    """Converte formato legado (model str) ou lista models para lista de ids."""
    modelos = credenciais.get('models')
    if isinstance(modelos, list):
        return [str(m) for m in modelos if m]
    model = credenciais.get('model')
    if model:
        return [str(model)]
    return []
