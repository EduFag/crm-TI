"""Sinônimos para retrieval por keyword (stack DeepSeek-only, sem embeddings)."""

from __future__ import annotations

# Cada grupo: se qualquer termo aparecer na query, injeta todos no score
GRUPOS_SINONIMOS: tuple[frozenset[str], ...] = (
    frozenset({
        'joytec', 'discador', 'ramal', 'ramais', 'campanha', 'campanhas',
        'licenca', 'licença', 'licencas', 'licenças', 'login_discador',
    }),
    frozenset({
        'moneyconsig', 'moneypromotora', 'ranking', 'abas', 'presenca',
        'presença', 'consig', 'sistema',
    }),
    frozenset({
        'chip', 'chips', 'whatsapp', 'wpp', 'linha', 'linhas', 'celular',
    }),
    frozenset({
        'acesso', 'acessos', 'login', 'senha', 'permissao', 'permissão',
        'usuario', 'usuário', 'crm',
    }),
    frozenset({
        'internet', 'rede', 'link', 'wifi', 'wi-fi', 'cabo', 'switch', 'roteador',
    }),
    frozenset({
        'anydesk', 'remoto', 'computador', 'notebook', 'hardware', 'mouse',
        'teclado', 'monitor',
    }),
    frozenset({
        'email', 'e-mail', 'outlook', 'caixa', 'conta',
    }),
)


def expandir_tokens_com_sinonimos(tokens: set[str]) -> set[str]:
    """Amplia o conjunto de tokens com grupos de sinônimos da empresa."""
    if not tokens:
        return tokens
    ampliados = set(tokens)
    for grupo in GRUPOS_SINONIMOS:
        if ampliados & grupo:
            ampliados |= set(grupo)
    return ampliados
