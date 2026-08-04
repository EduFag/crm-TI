"""Configuração de provedores de API externa (não-IA) e campos do wizard."""

from integracoes.models import IntegracaoApi

# Campos que ficam no model (não no blob de credenciais)
CAMPOS_META_API = frozenset({'name', 'provider', 'is_active'})

API_PROVIDER_CONFIG = {
    IntegracaoApi.Provider.MONEYCONSIG: {
        'label': 'MoneyConsig',
        'descricao': 'API B2B do sistema MoneyConsig (Bearer token)',
        'accent': 'emerald',
        'default_base_url': 'https://sistema.moneypromotora.com.br',
        'fields': [
            {
                'name': 'name',
                'label': 'Nome',
                'type': 'text',
                'required': True,
                'placeholder': 'Ex.: MoneyConsig produção',
            },
            {
                'name': 'api_token',
                'label': 'Token Bearer',
                'type': 'password',
                'required': True,
                'sensitive': True,
                'placeholder': 'mc_...',
            },
            {
                'name': 'base_url',
                'label': 'URL base',
                'type': 'text',
                'required': True,
                'placeholder': 'https://sistema.moneypromotora.com.br',
                'default': 'https://sistema.moneypromotora.com.br',
            },
        ],
    },
}


def config_do_provedor_api(provider: str) -> dict:
    return API_PROVIDER_CONFIG.get(provider) or {}


def campos_do_provedor_api(provider: str) -> list[dict]:
    """Campos preenchíveis pelo usuário."""
    return list(config_do_provedor_api(provider).get('fields') or [])


def default_base_url_api(provider: str) -> str:
    return config_do_provedor_api(provider).get('default_base_url', '')


def lista_provedores_api() -> list[dict]:
    itens = []
    for codigo, cfg in API_PROVIDER_CONFIG.items():
        itens.append({
            'codigo': codigo,
            'label': cfg['label'],
            'descricao': cfg['descricao'],
            'accent': cfg['accent'],
            'default_base_url': cfg.get('default_base_url', ''),
            'fields': list(cfg['fields']),
        })
    return itens
