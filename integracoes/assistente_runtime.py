"""Runtime do Assistente Helpdesk: tool-calling + serviços de escrita."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.db.models import Q

from helpdesk.assistente_services import (
    AssistenteServiceError,
    assistente_motivo_bloqueio,
    assistente_pode_atuar,
    atualizar_descricao_chamado,
    atualizar_observacao_chip,
    atualizar_solicitante,
    atualizar_status_chip,
    consultar_acesso_discador,
    consultar_chips,
    consultar_email,
    consultar_equipamento,
    consultar_licencas_discador,
    consultar_usuario,
    descrever_imagem_anexo,
    escalar_para_ti,
    extrair_texto_pdf_anexo,
    limpar_texto_para_solicitante,
    ler_anexo_como_texto,
    listar_anexos_ticket,
    listar_campanhas_discador,
    listar_categorias_especificas,
    listar_ramais_discador,
    recusar_chamado,
    send_assistente_message,
    set_ticket_priority,
    set_ticket_status,
    ticket_tem_orientacao_interna_pendente,
    triar_chamado,
)
from helpdesk.models import Comment, Ticket
from helpdesk.ticket_access import usuario_eh_operador_helpdesk
from integracoes.llm import LlmError, chat_completion
from integracoes.models import AssistenteChunk

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6

TOOLS_SPEC = [
    {
        'type': 'function',
        'function': {
            'name': 'send_assistente_message',
            'description': (
                'Envia uma mensagem CURTA. Por padrão (interno=false) vai ao solicitante. '
                'Com interno=true: só TI/staff vê (canal privado) — use para orientar a TI '
                'após triagem/escalonamento ou alinhar sem o solicitante ler. '
                'Chame de novo para a próxima fala pública — prefira 2–4 bolhas. '
                'O campo text: sem raciocínio, "Ok, vou...", "1ª mensagem:" ou planos. '
                'Use Markdown leve (**negrito**, listas).'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'text': {
                        'type': 'string',
                        'description': (
                            'Texto da mensagem (pública ao solicitante ou interna à TI).'
                        ),
                    },
                    'interno': {
                        'type': 'boolean',
                        'description': (
                            'true = só TI/staff/Assistente veem; false (padrão) = solicitante vê.'
                        ),
                    },
                },
                'required': ['text'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'set_ticket_priority',
            'description': 'Define só a prioridade do chamado (sem categoria). Prefira triar_chamado quando for triagem completa.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'priority': {
                        'type': 'string',
                        'enum': ['LOW', 'MEDIUM', 'HIGH', 'URGENT'],
                    },
                },
                'required': ['priority'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'set_ticket_status',
            'description': 'Altera a coluna/status do Kanban. Use RESOLVED só se o problema foi resolvido sem TI.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'status': {
                        'type': 'string',
                        'enum': ['NEW', 'IN_PROGRESS', 'PENDING', 'RESOLVED'],
                    },
                },
                'required': ['status'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'listar_categorias_especificas',
            'description': 'Lista categorias específicas ativas (id e nome) para usar em triar_chamado.',
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'triar_chamado',
            'description': (
                'Triagem: define prioridade e categoria específica do chamado '
                '(equivalente ao botão Triar da TI). Use listar_categorias_especificas antes se precisar do id.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'priority': {
                        'type': 'string',
                        'enum': ['LOW', 'MEDIUM', 'HIGH', 'URGENT'],
                    },
                    'specific_category_id': {
                        'type': 'integer',
                        'description': 'ID da categoria específica (opcional).',
                    },
                },
                'required': ['priority'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'recusar_chamado',
            'description': (
                'Recusa o chamado quando título/descrição não correspondem ao problema real. '
                'Exige motivo. Orienta abrir novo chamado correto.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'motivo': {'type': 'string'},
                },
                'required': ['motivo'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'listar_anexos',
            'description': (
                'Lista anexos do chamado (refs para ler_imagem_anexo / ler_pdf_anexo / '
                'ler_anexo_texto).'
            ),
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'ler_imagem_anexo',
            'description': (
                'Lê um print/imagem: visão multimodal se disponível, senão OCR local → texto. '
                'Use ref de listar_anexos (ticket:ID ou comment:ID). '
                'Se o contexto já trouxer texto dos anexos, use esses dados. '
                'NÃO peça ao solicitante descrever o print se o texto já explicar o pedido.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'attachment_ref': {
                        'type': 'string',
                        'description': 'Ex.: ticket:12 ou comment:34',
                    },
                },
                'required': ['attachment_ref'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'ler_pdf_anexo',
            'description': (
                'Extrai texto de um PDF anexado (texto nativo ou OCR local). '
                'Use quando listar_anexos mostrar is_pdf. '
                'Se o contexto já trouxer o texto do PDF, use esses dados.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'attachment_ref': {
                        'type': 'string',
                        'description': 'Ex.: ticket:12 ou comment:34',
                    },
                },
                'required': ['attachment_ref'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'ler_anexo_texto',
            'description': (
                'Converte imagem ou PDF em texto (visão/OCR/extração). '
                'Útil quando a IA do chat é só texto (ex.: DeepSeek).'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'attachment_ref': {'type': 'string'},
                },
                'required': ['attachment_ref'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'consultar_chips',
            'description': (
                'Consulta chips WhatsApp por nome do consultor ou número da linha '
                '(quantos em uso, status). NÃO cria nem registra chip novo — '
                'entrega/troca de chip é ação humana da TI (mensagem interna + escalar).'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'q': {'type': 'string', 'description': 'Nome do consultor ou número.'},
                },
                'required': ['q'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'atualizar_status_chip',
            'description': (
                'Altera o status do chip (ACTIVE|BANNED|CANCELED|LOST|OTHER). '
                'Passe chip_id ou line_number.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'chip_id': {'type': 'integer'},
                    'line_number': {'type': 'string'},
                    'status': {
                        'type': 'string',
                        'enum': ['ACTIVE', 'BANNED', 'CANCELED', 'LOST', 'OTHER'],
                    },
                },
                'required': ['status'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'atualizar_observacao_chip',
            'description': 'Atualiza a observação operacional do chip (chip_id ou line_number).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'chip_id': {'type': 'integer'},
                    'line_number': {'type': 'string'},
                    'observacao': {'type': 'string'},
                },
                'required': ['observacao'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'consultar_equipamento',
            'description': 'Consulta patrimônio/equipamento por tag, serial, modelo ou colaborador.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'q': {'type': 'string', 'description': 'Tag, serial, modelo ou nome.'},
                },
                'required': ['q'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'consultar_email',
            'description': 'Consulta e-mail corporativo por username, domínio ou nome do colaborador.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'q': {'type': 'string'},
                },
                'required': ['q'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'consultar_usuario',
            'description': (
                'Busca usuário CRM por username ou nome. '
                'results[].eh_membro_ti=true → é da TI (não use como solicitante). '
                'Use antes de atualizar_solicitante.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'q': {'type': 'string'},
                },
                'required': ['q'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'atualizar_solicitante',
            'description': (
                'Corrige o solicitante do chamado após confirmação. '
                'Se a pessoa tiver conta: passe user_id (de consultar_usuario). '
                'Se não tiver: passe nome_livre. '
                'Não use membro da TI (eh_membro_ti) como solicitante.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'user_id': {'type': 'integer', 'description': 'ID do usuário do sistema'},
                    'nome_livre': {
                        'type': 'string',
                        'description': 'Nome sem conta no sistema',
                    },
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'atualizar_descricao_chamado',
            'description': (
                'Reescreve a descrição (e opcionalmente o título) de forma clara e objetiva, '
                'após entender o problema real (ex.: loja X sem internet; aberto por Y em nome da unidade).'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'description': {'type': 'string'},
                    'title': {'type': 'string'},
                },
                'required': ['description'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'consultar_licencas_discador',
            'description': (
                'Inventário LOCAL do CRM (não acessa o site JoyTec): licenças contratadas, '
                'ramais FREE, em uso e slots no contrato. Em pedido de ramal: consulte e '
                'oriente a TI via send_assistente_message com interno=true '
                '(qual FREE usar OU se precisa comprar mais). Nunca crie/libere acesso.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'slug': {'type': 'string', 'description': 'Padrão joytec.'},
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'listar_ramais_discador',
            'description': (
                'Lista ramais do inventário local CRM. Filtre FREE|IN_USE|NOT_CONFIGURED. '
                'Só leitura — passe o FREE sugerido à TI em mensagem interna.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string', 'enum': ['FREE', 'IN_USE', 'NOT_CONFIGURED', '']},
                    'slug': {'type': 'string'},
                    'limit': {'type': 'integer'},
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'consultar_acesso_discador',
            'description': (
                'Busca no inventário local se a pessoa já tem acesso (titular, login, ramal). '
                'Senha não fica no CRM. Se já tiver, informe ao solicitante; se não, '
                'veja FREE e avise a TI em mensagem interna.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'q': {'type': 'string'},
                    'slug': {'type': 'string'},
                },
                'required': ['q'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'listar_campanhas_discador',
            'description': 'Lista campanhas do inventário local do discador (id e nome). Só leitura.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'slug': {'type': 'string'},
                },
                'required': [],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'escalar_para_ti',
            'description': (
                'Encerra o Assistente e pede técnico de TI. Use para MoneyConsig '
                '(sistema interno Money Promotora — sem API/MCP ainda), AnyDesk, hardware, '
                'permissões, ou quando o inventário discador estiver no limite (comprar ramais). '
                'Nunca diga que MoneyConsig é de terceiros.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'motivo': {'type': 'string'},
                },
                'required': [],
            },
        },
    },
]


def _tokens_relevancia(*textos: str) -> set[str]:
    """Extrai tokens úteis (len>=3) e amplia com sinônimos da empresa."""
    from integracoes.sinonimos_retrieval import expandir_tokens_com_sinonimos

    tokens: set[str] = set()
    for texto in textos:
        if not texto:
            continue
        for raw in re.split(r'[^\w]+', str(texto).lower(), flags=re.UNICODE):
            tok = raw.strip('_')
            if len(tok) >= 3:
                tokens.add(tok)
    return expandir_tokens_com_sinonimos(tokens)


def _score_chunk(chunk: AssistenteChunk, tokens: set[str], categoria: str) -> int:
    """Pontuação por match de categoria/tags/palavras-chave (DeepSeek-only)."""
    score = 0
    cat_hint = (chunk.categoria_hint or '').lower()
    titulo = (chunk.titulo or '').lower()
    conteudo = (chunk.conteudo or '').lower()
    tags = chunk.tags if isinstance(chunk.tags, list) else []
    tags_txt = ' '.join(str(t) for t in tags).lower()
    hay = f'{titulo} {conteudo} {cat_hint} {tags_txt}'

    if categoria:
        cat_l = categoria.lower()
        cat_tokens = _tokens_relevancia(categoria)
        if cat_l in cat_hint or cat_hint in cat_l:
            score += 12
        elif any(t in cat_hint for t in cat_tokens if len(t) >= 4):
            score += 8
        elif cat_l in titulo or cat_l in conteudo:
            score += 5

    # Tags explícitas pesam mais (curadoria manual)
    for tok in tokens:
        if tok in tags_txt:
            score += 5
        elif tok in titulo or tok in cat_hint:
            score += 3
        elif tok in conteudo:
            score += 1
    return score


def _chunks_relevantes(ticket: Ticket, limite: int = 12) -> tuple[list[AssistenteChunk], bool]:
    """Seleciona chunks ativos: regras sempre + demais por score híbrido.

    Retorna (chunks, usou_embedding_na_query).
    """
    from integracoes.embeddings import cosine_similarity, score_hibrido
    from integracoes.llm import LlmError, obter_embedding, obter_integracao_embedding
    from integracoes.regras_seed import chunk_eh_regra, garantir_chunks_regras

    # Garante seeds se a migration ainda não rodou ou banco novo
    garantir_chunks_regras()

    qs = list(AssistenteChunk.objects.filter(ativo=True)[:300])
    if not qs:
        return [], False

    regras = [ch for ch in qs if chunk_eh_regra(ch)]
    demais = [ch for ch in qs if not chunk_eh_regra(ch)]

    cat = ticket.category.name if ticket.category_id else ''
    query_txt = ' '.join([
        ticket.title or '',
        (ticket.description or '')[:800],
        cat,
        ticket.specific_category.name if ticket.specific_category_id else '',
    ]).strip()
    tokens = _tokens_relevancia(ticket.title or '', (ticket.description or '')[:800], cat)
    if ticket.specific_category_id:
        tokens |= _tokens_relevancia(ticket.specific_category.name)

    query_emb: list[float] | None = None
    if obter_integracao_embedding() and query_txt:
        try:
            query_emb, _ = obter_embedding(query_txt)
        except LlmError as exc:
            logger.info('embedding query ticket=%s indisponível: %s', ticket.pk, exc)

    kw_scores = {_score_chunk(ch, tokens, cat) for ch in demais} or {0}
    keyword_max = float(max(kw_scores)) if kw_scores else 1.0
    if keyword_max <= 0:
        keyword_max = 1.0

    def _chave_hibrida(ch: AssistenteChunk) -> tuple:
        kw = float(_score_chunk(ch, tokens, cat))
        emb = ch.embedding if isinstance(ch.embedding, list) and ch.embedding else None
        cos = cosine_similarity(query_emb, emb) if query_emb and emb else 0.0
        h = score_hibrido(kw, keyword_max, cos, bool(emb and query_emb))
        return (
            h,
            ch.atualizado_em.timestamp() if ch.atualizado_em else 0,
        )

    ranqueados = sorted(demais, key=_chave_hibrida, reverse=True)
    # Mantém quem tem algum sinal (keyword ou semântico)
    com_score = []
    for ch in ranqueados:
        kw = float(_score_chunk(ch, tokens, cat))
        emb = ch.embedding if isinstance(ch.embedding, list) and ch.embedding else None
        cos = cosine_similarity(query_emb, emb) if query_emb and emb else 0.0
        if kw > 0 or cos > 0.25:
            com_score.append(ch)
    if not com_score:
        com_score = ranqueados

    escolhidos: list[AssistenteChunk] = list(regras)
    ids_ja = {ch.pk for ch in escolhidos}
    vagas = max(0, limite - len(escolhidos))
    for ch in com_score:
        if vagas <= 0:
            break
        if ch.pk in ids_ja:
            continue
        escolhidos.append(ch)
        ids_ja.add(ch.pk)
        vagas -= 1

    hybrid = bool(query_emb)
    logger.info(
        'chunks_relevantes ticket=%s regras=%s ids=%s hybrid=%s',
        ticket.pk,
        [ch.pk for ch in regras],
        [ch.pk for ch in escolhidos],
        hybrid,
    )
    return escolhidos, hybrid


def buscar_chunks(q: str = '', limite: int = 20, so_ativos: bool = True) -> list[AssistenteChunk]:
    """Busca chunks por relevância híbrida (keyword + embedding). Usado pela API MCP."""
    from integracoes.embeddings import cosine_similarity, score_hibrido
    from integracoes.llm import LlmError, obter_embedding, obter_integracao_embedding

    qs = AssistenteChunk.objects.all()
    if so_ativos:
        qs = qs.filter(ativo=True)
    chunks = list(qs[:300])
    if not chunks:
        return []
    texto = (q or '').strip()
    if not texto:
        return chunks[: max(1, min(limite, 50))]

    tokens = _tokens_relevancia(texto)
    query_emb: list[float] | None = None
    if obter_integracao_embedding():
        try:
            query_emb, _ = obter_embedding(texto)
        except LlmError:
            query_emb = None

    kw_scores = {_score_chunk(ch, tokens, texto) for ch in chunks} or {0}
    keyword_max = float(max(kw_scores)) if kw_scores else 1.0
    if keyword_max <= 0:
        keyword_max = 1.0

    def _chave(ch: AssistenteChunk) -> tuple:
        kw = float(_score_chunk(ch, tokens, texto))
        emb = ch.embedding if isinstance(ch.embedding, list) and ch.embedding else None
        cos = cosine_similarity(query_emb, emb) if query_emb and emb else 0.0
        h = score_hibrido(kw, keyword_max, cos, bool(emb and query_emb))
        return (h, ch.atualizado_em.timestamp() if ch.atualizado_em else 0)

    ranqueados = sorted(chunks, key=_chave, reverse=True)
    com_score = []
    for ch in ranqueados:
        kw = float(_score_chunk(ch, tokens, texto))
        emb = ch.embedding if isinstance(ch.embedding, list) and ch.embedding else None
        cos = cosine_similarity(query_emb, emb) if query_emb and emb else 0.0
        if kw > 0 or cos > 0.25:
            com_score.append(ch)
    return (com_score or ranqueados)[: max(1, min(limite, 50))]


def _resumo_anexos(ticket: Ticket) -> str:
    try:
        data = listar_anexos_ticket(ticket.pk)
    except AssistenteServiceError:
        return '(falha ao listar anexos)'
    itens = data.get('results') or []
    if not itens:
        return '(nenhum anexo)'
    linhas = []
    for a in itens:
        if a.get('is_image'):
            tipo = 'imagem'
        elif a.get('is_pdf'):
            tipo = 'pdf'
        else:
            tipo = 'arquivo'
        linhas.append(f"- {a.get('ref')} [{tipo}] {a.get('nome')}")
    return '\n'.join(linhas)


def _montar_contexto(ticket: Ticket) -> tuple[str, list[int], bool]:
    """Monta o contexto do chamado. Retorna (texto, chunk_ids, hybrid)."""
    comentarios = (
        Comment.objects.filter(ticket=ticket, is_active=True)
        .select_related('author')
        .order_by('created_at')[:40]
    )
    linhas = []
    for c in comentarios:
        if c.is_assistente:
            autor = 'Assistente'
        elif c.author_id:
            autor = c.author.get_full_name() or c.author.username
        else:
            autor = 'Sistema'
        marca = ' [INTERNO TI]' if c.is_interno else ''
        extra = ' [tem anexo]' if c.attachment else ''
        linhas.append(f'[{autor}]{marca}{extra} {c.text}')

    chunks, hybrid = _chunks_relevantes(ticket)
    from integracoes.regras_seed import chunk_eh_regra

    regras_txt = '\n'.join(
        f'- {ch.titulo}: {ch.conteudo}' for ch in chunks if chunk_eh_regra(ch)
    ) or '(sem regras seed)'
    aprendizado_txt = '\n'.join(
        f'- {ch.titulo}: {ch.conteudo}' for ch in chunks if not chunk_eh_regra(ch)
    ) or '(sem chunks de aprendizado)'
    cat_esp = ticket.specific_category.name if ticket.specific_category_id else '(não triado)'
    equipe_nome = ticket.equipe.name if ticket.equipe_id else '(não informada)'

    if ticket.requester_user_id:
        ru = ticket.requester_user
        sol_txt = (
            f'{ticket.requester_name} (@{ru.username}, user_id={ru.pk})'
        )
        if usuario_eh_operador_helpdesk(ru):
            sol_txt += ' [ATENÇÃO: solicitante é membro da TI]'
        else:
            sol_txt += ' [usuário do sistema]'
    else:
        sol_txt = f'{ticket.requester_name} [nome livre, sem user vinculado]'

    criador_txt = '-'
    if ticket.created_by_id:
        cb = ticket.created_by
        criador_txt = cb.get_full_name() or cb.username
        if usuario_eh_operador_helpdesk(cb):
            criador_txt += ' [membro da TI]'

    texto = (
        f'Chamado #{ticket.pk}\n'
        f'Título: {ticket.title}\n'
        f'Descrição: {ticket.description}\n'
        f'Status: {ticket.status}\n'
        f'Prioridade: {ticket.priority or "(não definida)"}\n'
        f'Categoria: {ticket.category.name if ticket.category_id else "-"}\n'
        f'Categoria específica: {cat_esp}\n'
        f'Equipe/Setor (unidade afetada — NÃO é o solicitante): {equipe_nome}\n'
        f'Solicitante: {sol_txt}\n'
        f'Aberto por (created_by): {criador_txt}\n'
        f'Atribuído a: {(ticket.assigned_to.username if ticket.assigned_to_id else "(ninguém)")}\n\n'
        f'Anexos:\n{_resumo_anexos(ticket)}\n\n'
        f'Histórico de comentários:\n' + ('\n'.join(linhas) or '(vazio)') + '\n\n'
        f'Regras de negócio (obrigatórias):\n{regras_txt}\n\n'
        f'Aprendizado (estilo TI / chunks):\n{aprendizado_txt}'
    )
    return texto, [ch.pk for ch in chunks], hybrid



def _system_prompt() -> str:
    """Persona curta: regras de negócio ficam nos chunks com tag regra."""
    return (
        'Você é o Assistente de TI da Money Promotora no helpdesk. '
        'Responda em português, claro e profissional.\n\n'
        'Siga SEMPRE as "Regras de negócio (obrigatórias)" e o "Aprendizado" do contexto, '
        'além das tools disponíveis. '
        'Não invente procedimentos fora desses chunks e do histórico do chamado.\n\n'
        'Lembretes fixos:\n'
        '- Sempre envie ao menos uma mensagem via send_assistente_message nesta interação.\n'
        '- Use Markdown leve; ao solicitante prefira 2–4 bolhas curtas.\n'
        '- O campo text das mensagens não deve conter raciocínio interno nem rótulos '
        '("1ª mensagem:", "Vou verificar…").\n'
        '- Se Prioridade estiver "(não definida)", tria com triar_chamado nesta interação.\n'
        '- Discador JoyTec: só inventário local (consulta). Não cria/libera acesso; '
        'oriente a TI com send_assistente_message interno=true.\n'
        '- Chips WhatsApp: só consultar e atualizar status/obs. Não cria chip novo '
        'nem entrega chip reserva — use mensagem interna + escalar_para_ti.\n'
        '- MoneyConsig: sistema interno; sem API — use escalar_para_ti.'
    )


def _executar_tool(ticket_id: int, name: str, args: dict) -> str:
    try:
        if name == 'send_assistente_message':
            return json.dumps(
                send_assistente_message(
                    ticket_id,
                    args.get('text', ''),
                    interno=bool(args.get('interno')),
                ),
                ensure_ascii=False,
            )
        if name == 'set_ticket_priority':
            return json.dumps(set_ticket_priority(ticket_id, args.get('priority', '')), ensure_ascii=False)
        if name == 'set_ticket_status':
            return json.dumps(set_ticket_status(ticket_id, args.get('status', '')), ensure_ascii=False)
        if name == 'listar_categorias_especificas':
            return json.dumps(listar_categorias_especificas(), ensure_ascii=False)
        if name == 'triar_chamado':
            return json.dumps(
                triar_chamado(
                    ticket_id,
                    args.get('priority', ''),
                    args.get('specific_category_id'),
                ),
                ensure_ascii=False,
            )
        if name == 'recusar_chamado':
            return json.dumps(recusar_chamado(ticket_id, args.get('motivo', '')), ensure_ascii=False)
        if name == 'listar_anexos':
            return json.dumps(listar_anexos_ticket(ticket_id), ensure_ascii=False)
        if name == 'ler_imagem_anexo':
            return json.dumps(
                descrever_imagem_anexo(ticket_id, args.get('attachment_ref', '')),
                ensure_ascii=False,
            )
        if name == 'ler_pdf_anexo':
            return json.dumps(
                extrair_texto_pdf_anexo(ticket_id, args.get('attachment_ref', '')),
                ensure_ascii=False,
            )
        if name == 'ler_anexo_texto':
            return json.dumps(
                ler_anexo_como_texto(ticket_id, args.get('attachment_ref', '')),
                ensure_ascii=False,
            )
        if name == 'consultar_chips':
            return json.dumps(consultar_chips(args.get('q', '')), ensure_ascii=False)
        if name == 'atualizar_status_chip':
            return json.dumps(
                atualizar_status_chip(
                    args.get('chip_id'),
                    args.get('line_number') or '',
                    args.get('status', ''),
                ),
                ensure_ascii=False,
            )
        if name == 'atualizar_observacao_chip':
            return json.dumps(
                atualizar_observacao_chip(
                    args.get('chip_id'),
                    args.get('line_number') or '',
                    args.get('observacao', ''),
                ),
                ensure_ascii=False,
            )
        if name == 'consultar_equipamento':
            return json.dumps(consultar_equipamento(args.get('q', '')), ensure_ascii=False)
        if name == 'consultar_email':
            return json.dumps(consultar_email(args.get('q', '')), ensure_ascii=False)
        if name == 'consultar_usuario':
            return json.dumps(consultar_usuario(args.get('q', '')), ensure_ascii=False)
        if name == 'atualizar_solicitante':
            return json.dumps(
                atualizar_solicitante(
                    ticket_id,
                    args.get('user_id'),
                    args.get('nome_livre', ''),
                ),
                ensure_ascii=False,
            )
        if name == 'atualizar_descricao_chamado':
            return json.dumps(
                atualizar_descricao_chamado(
                    ticket_id,
                    args.get('description', ''),
                    args.get('title'),
                ),
                ensure_ascii=False,
            )
        if name == 'consultar_licencas_discador':
            return json.dumps(
                consultar_licencas_discador(args.get('slug') or 'joytec'),
                ensure_ascii=False,
            )
        if name == 'listar_ramais_discador':
            return json.dumps(
                listar_ramais_discador(
                    args.get('status') or '',
                    args.get('slug') or 'joytec',
                    args.get('limit') or 40,
                ),
                ensure_ascii=False,
            )
        if name == 'consultar_acesso_discador':
            return json.dumps(
                consultar_acesso_discador(
                    args.get('q', ''),
                    args.get('slug') or 'joytec',
                ),
                ensure_ascii=False,
            )
        if name == 'listar_campanhas_discador':
            return json.dumps(
                listar_campanhas_discador(args.get('slug') or 'joytec'),
                ensure_ascii=False,
            )
        if name == 'escalar_para_ti':
            return json.dumps(escalar_para_ti(ticket_id, args.get('motivo', '')), ensure_ascii=False)
        return json.dumps({'ok': False, 'error': f'Tool desconhecida: {name}'})
    except AssistenteServiceError as exc:
        return json.dumps({'ok': False, 'error': str(exc)})
    except (TypeError, ValueError) as exc:
        return json.dumps({'ok': False, 'error': f'Argumentos inválidos: {exc}'})


def _parse_args(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


_MSG_FALLBACK = (
    'Olá! Recebi seu chamado e estou analisando. Em breve retorno com orientações '
    'ou encaminho para a equipe de TI.'
)
_MSG_FALLBACK_ERRO = (
    'Olá! Recebi seu chamado. Estou com dificuldade técnica no momento; '
    'a equipe de TI já pode acompanhar por aqui.'
)


def _rodada_tools(
    ticket_id: int,
    messages: list[dict[str, Any]],
    *,
    enviou_mensagem: bool,
) -> bool:
    """Uma rodada de tool-calling; devolve se enviou mensagem nesta rodada/acumulado."""
    ticket = Ticket.objects.get(pk=ticket_id)
    if not assistente_pode_atuar(ticket) and enviou_mensagem:
        return enviou_mensagem
    if (
        ticket.assistente_escalado
        and enviou_mensagem
        and not ticket_tem_orientacao_interna_pendente(ticket)
    ):
        return enviou_mensagem
    if ticket.is_rejected and enviou_mensagem:
        return enviou_mensagem

    msg = chat_completion(messages, tools=TOOLS_SPEC, temperature=0.35)
    tool_calls = msg.get('tool_calls') or []
    messages.append(msg)

    if not tool_calls:
        # content sem tools costuma ser raciocínio — só posta se sobrar fala limpa
        content = limpar_texto_para_solicitante(msg.get('content') or '')
        if content and not enviou_mensagem:
            try:
                send_assistente_message(ticket_id, content)
                enviou_mensagem = True
            except AssistenteServiceError:
                pass
        return enviou_mensagem

    for call in tool_calls:
        fn = call.get('function') or {}
        name = fn.get('name') or ''
        args = _parse_args(fn.get('arguments'))
        result = _executar_tool(ticket_id, name, args)
        try:
            parsed = json.loads(result)
            if name == 'send_assistente_message' and parsed.get('ok'):
                enviou_mensagem = True
            if name == 'recusar_chamado' and parsed.get('ok'):
                enviou_mensagem = True
            if name == 'escalar_para_ti' and parsed.get('ok'):
                enviou_mensagem = True
        except json.JSONDecodeError:
            pass
        messages.append({
            'role': 'tool',
            'tool_call_id': call.get('id') or name,
            'content': result,
        })
    return enviou_mensagem


def _garantir_triagem(ticket_id: int, messages: list[dict[str, Any]]) -> None:
    """Se ainda sem prioridade, pede triagem à IA; senão aplica MEDIUM."""
    ticket = Ticket.objects.get(pk=ticket_id)
    if ticket.priority or not assistente_pode_atuar(ticket):
        return

    messages.append({
        'role': 'user',
        'content': (
            'Prioridade ainda não definida. Obrigatório agora: '
            'listar_categorias_especificas se precisar do id, depois triar_chamado. '
            'Não envie mensagem longa — só a triagem.'
        ),
    })
    try:
        _rodada_tools(ticket_id, messages, enviou_mensagem=True)
    except (LlmError, AssistenteServiceError, Exception):
        logger.exception('Falha na rodada extra de triagem do ticket %s', ticket_id)

    ticket.refresh_from_db()
    if not ticket.priority and assistente_pode_atuar(ticket):
        try:
            triar_chamado(ticket_id, 'MEDIUM', None)
            logger.info(
                'Triagem fallback MEDIUM aplicada no ticket %s',
                ticket_id,
            )
        except AssistenteServiceError:
            logger.exception('Falha no fallback de triagem do ticket %s', ticket_id)


def _textos_anexos_prelidos(ticket_id: int) -> str:
    """Pré-lê imagens e PDFs → texto (visão ou OCR/extração local)."""
    try:
        data = listar_anexos_ticket(ticket_id)
    except AssistenteServiceError:
        return ''
    anexos = [
        a for a in (data.get('results') or [])
        if a.get('is_image') or a.get('is_pdf')
    ]
    if not anexos:
        return ''

    linhas = []
    for a in anexos[:4]:
        ref = a.get('ref') or ''
        nome = a.get('nome') or ref
        tipo = 'pdf' if a.get('is_pdf') else 'imagem'
        try:
            res = ler_anexo_como_texto(ticket_id, ref)
            desc = (res.get('descricao') or '').strip()
            metodo = res.get('metodo') or ''
            linhas.append(f'- {ref} [{tipo}/{metodo}] ({nome}): {desc}')
        except AssistenteServiceError as exc:
            logger.warning('Falha ao pré-ler anexo %s ticket %s: %s', ref, ticket_id, exc)
            linhas.append(f'- {ref} ({nome}): [falha ao ler {tipo}: {exc}]')
        except Exception:
            logger.exception('Erro inesperado ao pré-ler anexo %s', ref)
            linhas.append(f'- {ref} ({nome}): [erro ao ler {tipo}]')
    return '\n'.join(linhas)


def _registrar_interacao(ticket_id: int, chunk_ids: list[int], hybrid: bool) -> None:
    """Persiste eval da rodada; nunca interrompe o atendimento."""
    try:
        from integracoes.models import AssistenteInteracao

        AssistenteInteracao.objects.create(
            ticket_id=ticket_id,
            chunk_ids=list(chunk_ids or []),
            hybrid=bool(hybrid),
        )
    except Exception:
        logger.exception('Falha ao registrar AssistenteInteracao ticket=%s', ticket_id)


def processar_assistente(ticket_id: int) -> None:
    """Processa uma rodada do Assistente no chamado. Seguro para on_commit/thread."""
    try:
        ticket = Ticket.objects.select_related(
            'category', 'specific_category', 'created_by', 'assigned_to',
            'requester_user', 'equipe',
        ).get(pk=ticket_id)
    except Ticket.DoesNotExist:
        return

    motivo = assistente_motivo_bloqueio(ticket)
    if motivo:
        logger.info(
            'Assistente não atuou no ticket %s: %s',
            ticket_id,
            motivo,
        )
        return

    chunk_ids: list[int] = []
    hybrid = False
    contexto_ok = False
    try:
        contexto, chunk_ids, hybrid = _montar_contexto(ticket)
        contexto_ok = True
        textos_anexos = _textos_anexos_prelidos(ticket_id)
        if textos_anexos:
            contexto += (
                '\n\nTexto dos anexos (imagem/PDF já convertidos — visão ou OCR/extração local; '
                'use estes dados; não diga que não conseguiu ver o anexo):\n' + textos_anexos
            )
            if 'falha ao ler' in textos_anexos.lower() or 'erro ao ler' in textos_anexos.lower():
                contexto += (
                    '\n\nNota: alguma leitura de anexo falhou. NÃO peça ao solicitante para '
                    'descrever o arquivo se título/descrição/categoria já explicarem o pedido. '
                    'MoneyConsig é sistema INTERNO da Money Promotora; escale para a TI interna.'
                )

        orientacao_interna = ticket_tem_orientacao_interna_pendente(ticket)
        pedido = 'Analise o chamado e aja (tools). Contexto:\n\n' + contexto
        if orientacao_interna:
            pedido += (
                '\n\nHá orientação INTERNA recente da TI ([INTERNO TI]). '
                'Priorize: se pedirem correção do que você falou, mande mensagem PÚBLICA '
                'corrigindo o solicitante; se pedirem só nota à TI, use interno=true. '
                'Não mencione o canal privado ao solicitante.'
            )

        messages: list[dict[str, Any]] = [
            {'role': 'system', 'content': _system_prompt()},
            {'role': 'user', 'content': pedido},
        ]

        enviou_mensagem = False
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                ticket.refresh_from_db()
                if not assistente_pode_atuar(ticket) and enviou_mensagem:
                    break
                # Após escalar, ainda permite terminar se veio de orientação interna
                if (
                    ticket.assistente_escalado
                    and enviou_mensagem
                    and not ticket_tem_orientacao_interna_pendente(ticket)
                ):
                    break
                if ticket.is_rejected and enviou_mensagem:
                    break

                qtd_msgs = len(messages)
                enviou_mensagem = _rodada_tools(
                    ticket_id, messages, enviou_mensagem=enviou_mensagem,
                )
                # Resposta sem tools → fim
                last = messages[-1] if messages else {}
                if last.get('role') == 'assistant' and not (last.get('tool_calls') or []):
                    break
                # Nada novo anexado (proteção)
                if len(messages) == qtd_msgs:
                    break

            if (
                not enviou_mensagem
                and not orientacao_interna
                and assistente_pode_atuar(Ticket.objects.get(pk=ticket_id))
            ):
                send_assistente_message(ticket_id, _MSG_FALLBACK)
                enviou_mensagem = True

            if not orientacao_interna:
                _garantir_triagem(ticket_id, messages)
        except (LlmError, AssistenteServiceError, Exception):
            logger.exception('Falha ao processar Assistente no ticket %s', ticket_id)
            # Best-effort: chamado não fica mudo se o LLM falhar (exceto trigger só-interno)
            try:
                if (
                    not enviou_mensagem
                    and not orientacao_interna
                    and assistente_pode_atuar(Ticket.objects.get(pk=ticket_id))
                ):
                    send_assistente_message(ticket_id, _MSG_FALLBACK_ERRO)
            except Exception:
                logger.exception(
                    'Falha ao enviar fallback do Assistente no ticket %s',
                    ticket_id,
                )
            if not orientacao_interna:
                try:
                    _garantir_triagem(ticket_id, messages)
                except Exception:
                    pass
    finally:
        # Sempre registra eval desta rodada (mesmo se LLM falhou após montar contexto)
        if contexto_ok:
            _registrar_interacao(ticket_id, chunk_ids, hybrid)


def _titulo_normalizado(titulo: str) -> str:
    return re.sub(r'\s+', ' ', (titulo or '').strip().lower())


def gerar_chunks_aprendizado(
    limite_tickets: int = 30,
    data_inicio=None,
    data_fim=None,
) -> dict:
    """Usa a IA para gerar chunks a partir de chamados finalizados/arquivados.

    Substitui apenas chunks com origem=ia; preserva manual e chat.
    data_inicio/data_fim: date ou None (filtra resolved_at, fallback updated_at).
    """
    from datetime import datetime, time

    from django.utils import timezone

    from integracoes.llm import chat_text
    from integracoes.models import AssistenteChunk, AssistenteConfig

    limite_tickets = max(1, min(int(limite_tickets or 30), 80))
    qs = Ticket.objects.filter(
        Q(status=Ticket.StatusChoices.RESOLVED) | Q(is_archived=True)
    ).select_related('category').prefetch_related('comments', 'comments__author')

    if data_inicio or data_fim:
        # Intervalo sobre resolved_at; se nulo, usa updated_at
        if data_inicio:
            ini = timezone.make_aware(datetime.combine(data_inicio, time.min))
            qs = qs.filter(
                Q(resolved_at__gte=ini)
                | Q(resolved_at__isnull=True, updated_at__gte=ini)
            )
        if data_fim:
            fim = timezone.make_aware(
                datetime.combine(data_fim, time.max.replace(microsecond=0))
            )
            qs = qs.filter(
                Q(resolved_at__lte=fim)
                | Q(resolved_at__isnull=True, updated_at__lte=fim)
            )

    tickets = list(qs.order_by('-resolved_at', '-updated_at')[:limite_tickets])
    if not tickets:
        raise LlmError('Não há chamados resolvidos/arquivados no período para aprender.')

    blocos = []
    ids = []
    for t in tickets:
        ids.append(t.pk)
        comps = []
        for c in t.comments.filter(is_active=True).order_by('created_at')[:20]:
            if c.is_assistente:
                autor = 'Assistente'
            elif c.author_id:
                autor = c.author.username
            else:
                autor = 'Sistema'
            marca = ' [INTERNO TI]' if c.is_interno else ''
            comps.append(f'  - {autor}{marca}: {c.text[:400]}')
        blocos.append(
            f'#{t.pk} [{t.category.name if t.category_id else "-"}] {t.title}\n'
            f'Desc: {t.description[:500]}\nComentários:\n' + '\n'.join(comps)
        )

    periodo_txt = ''
    if data_inicio or data_fim:
        periodo_txt = (
            f' Período: {data_inicio or "…"} a {data_fim or "…"}.'
        )

    from integracoes.assistente_limites import prompt_limitacoes_aprendizado

    prompt = (
        'Com base nos chamados de helpdesk abaixo (já finalizados pela TI real), '
        'gere um JSON array de objetos com chaves: titulo, conteudo, categoria_hint, '
        'fonte_ticket_ids (lista opcional de IDs numéricos dos chamados que motivaram o chunk), '
        'tags (lista opcional de strings curtas). '
        'Priorize padrões das notas [INTERNO TI] (como a TI resolveu). '
        'Cada item é um "chunk" de aprendizado (tom de resposta, padrões, o que perguntar, '
        'quando escalar). Gere entre 5 e 12 chunks. '
        'IMPORTANTE: os chunks serão usados pelo Assistente automático — '
        'escreva só ações compatíveis com as limitações abaixo; se a TI humana '
        'fez algo que a IA não pode (ex.: criar/entregar chip), ensine a IA a '
        'consultar/atualizar o que puder e escalar/avisar a TI para o resto. '
        f'conteudo com no máximo 1200 caracteres.{periodo_txt}\n\n'
        f'{prompt_limitacoes_aprendizado()}\n\n'
        'Responda SOMENTE o JSON.\n\n'
        + '\n\n---\n\n'.join(blocos)
    )
    raw = chat_text([
        {
            'role': 'system',
            'content': (
                'Você extrai padrões de atendimento de TI para o Assistente automático. '
                'Nunca ensine ações fora das tools disponíveis (ex.: criar chip). '
                'Responda só JSON válido.'
            ),
        },
        {'role': 'user', 'content': prompt},
    ], temperature=0.3)

    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not match:
        raise LlmError('IA não retornou JSON de chunks.')
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise LlmError('JSON de chunks inválido.') from exc
    if not isinstance(data, list) or not data:
        raise LlmError('JSON de chunks vazio.')

    # Só remove chunks gerados pela IA; curadoria manual/chat permanece
    removidos = AssistenteChunk.objects.filter(origem=AssistenteChunk.Origem.IA).delete()[0]
    preservados = AssistenteChunk.objects.filter(
        origem__in=[AssistenteChunk.Origem.MANUAL, AssistenteChunk.Origem.CHAT],
        ativo=True,
    ).count()
    titulos_existentes = {
        _titulo_normalizado(t)
        for t in AssistenteChunk.objects.filter(ativo=True).values_list('titulo', flat=True)
    }

    criados = 0
    for item in data:
        if not isinstance(item, dict):
            continue
        titulo = (item.get('titulo') or '').strip()
        conteudo = (item.get('conteudo') or '').strip()
        if not titulo or not conteudo:
            continue
        if len(conteudo) > 1200:
            conteudo = conteudo[:1200].rstrip()
        norm = _titulo_normalizado(titulo)
        if not norm or norm in titulos_existentes:
            continue

        fontes = item.get('fonte_ticket_ids')
        if isinstance(fontes, list):
            fontes_ok = []
            for x in fontes:
                try:
                    n = int(x)
                except (TypeError, ValueError):
                    continue
                if n in ids:
                    fontes_ok.append(n)
            fonte_ticket_ids = fontes_ok or list(ids)
        else:
            fonte_ticket_ids = list(ids)

        tags_raw = item.get('tags')
        tags = []
        if isinstance(tags_raw, list):
            for tag in tags_raw[:8]:
                t = str(tag).strip()[:40]
                if t:
                    tags.append(t)

        chunk_novo = AssistenteChunk.objects.create(
            titulo=titulo[:200],
            conteudo=conteudo,
            categoria_hint=(item.get('categoria_hint') or '')[:120],
            fonte_ticket_ids=fonte_ticket_ids,
            origem=AssistenteChunk.Origem.IA,
            ativo=True,
            tags=tags,
        )
        from integracoes.embeddings import atualizar_embedding_chunk
        atualizar_embedding_chunk(chunk_novo)
        titulos_existentes.add(norm)
        criados += 1

    config = AssistenteConfig.get_solo()
    config.ultima_geracao_em = timezone.now()
    config.save(update_fields=['ultima_geracao_em', 'atualizado_em'])
    return {
        'ok': True,
        'chunks': criados,
        'tickets_analisados': len(ids),
        'removidos_ia': removidos,
        'preservados_curadoria': preservados,
    }
