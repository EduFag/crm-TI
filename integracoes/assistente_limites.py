"""Limitações reais das tools do Assistente Helpdesk.

Usado em prompts de análise/reanálise, orientação e curadoria de memória,
para que o aprendizado não invente ações que a IA não consegue executar.
"""

from __future__ import annotations

# Texto reutilizável nos prompts de geração de chunks
LIMITACOES_TOOLS_TEXTO = (
    'LIMITAÇÕES OBRIGATÓRIAS do Assistente (respeite ao escrever cada chunk):\n'
    '- Pode: consultar e atualizar status/observação de chips; consultar patrimônio, '
    'e-mail e usuário; consultar inventário local do Discador (licenças/ramais/acesso/'
    'campanhas); consultar/criar alertas e usuários no MoneyConsig (API B2B); '
    'enviar mensagem (pública ou interna à TI); triar/recusar/escalar; '
    'ler anexos (imagem/PDF/texto); alterar prioridade/status/solicitante/descrição.\n'
    '- NÃO pode criar chip novo, registrar chip operacional, entregar/devolver chip '
    'nem inventariar chip reserva. Banimento permanente / troca de chip = '
    'atualizar_status_chip se couber, mensagem interna à TI e escalar_para_ti '
    '(humano entrega o chip).\n'
    '- NÃO pode criar/liberar acesso Discador JoyTec nem comprar ramais. Só consulta '
    'o inventário local e oriente a TI via mensagem interna.\n'
    '- MoneyConsig: use tools moneyconsig_*; se a API estiver indisponível ou o caso '
    'for UI/abas/acessos humanos → escalar_para_ti (TI interna).\n'
    '- NÃO invente tools ou passos que a IA execute sozinha se a ação for só humana '
    '(entrega física, compra, suporte JoyTec externo, alteração de UI MoneyConsig).\n'
    '- Nos chunks, descreva o que a IA DEVE fazer com as tools acima; quando a TI '
    'humana precisa agir, diga explicitamente "escalar / mensagem interna à TI".'
)


def prompt_limitacoes_aprendizado() -> str:
    """Bloco pronto para colar em prompts de análise/orientação."""
    return LIMITACOES_TOOLS_TEXTO
