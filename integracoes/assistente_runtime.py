"""Runtime do Assistente Helpdesk: tool-calling + serviços de escrita."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.db.models import Q

from helpdesk.assistente_services import (
    AssistenteServiceError,
    assistente_pode_atuar,
    escalar_para_ti,
    send_assistente_message,
    set_ticket_priority,
    set_ticket_status,
)
from helpdesk.models import Comment, Ticket
from integracoes.llm import LlmError, chat_completion
from integracoes.models import AssistenteChunk

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 4

TOOLS_SPEC = [
    {
        'type': 'function',
        'function': {
            'name': 'send_assistente_message',
            'description': 'Envia uma mensagem ao solicitante no chamado (como Assistente).',
            'parameters': {
                'type': 'object',
                'properties': {
                    'text': {'type': 'string', 'description': 'Texto da mensagem em português.'},
                },
                'required': ['text'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'set_ticket_priority',
            'description': 'Define a prioridade do chamado.',
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
            'name': 'escalar_para_ti',
            'description': 'Encerra o atendimento do Assistente e pede um técnico de TI.',
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


def _chunks_relevantes(ticket: Ticket, limite: int = 8) -> list[AssistenteChunk]:
    qs = AssistenteChunk.objects.all()
    cat = ''
    if ticket.category_id:
        cat = ticket.category.name
    if cat:
        filtrados = list(qs.filter(Q(categoria_hint__icontains=cat) | Q(conteudo__icontains=cat))[:limite])
        if filtrados:
            return filtrados
    return list(qs[:limite])


def _montar_contexto(ticket: Ticket) -> str:
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
        linhas.append(f'[{autor}] {c.text}')

    chunks = _chunks_relevantes(ticket)
    chunks_txt = '\n'.join(f'- {ch.titulo}: {ch.conteudo}' for ch in chunks) or '(sem chunks ainda)'

    return (
        f'Chamado #{ticket.pk}\n'
        f'Título: {ticket.title}\n'
        f'Descrição: {ticket.description}\n'
        f'Status: {ticket.status}\n'
        f'Prioridade: {ticket.priority or "(não definida)"}\n'
        f'Categoria: {ticket.category.name if ticket.category_id else "-"}\n'
        f'Solicitante: {ticket.requester_name}\n'
        f'Criador: {(ticket.created_by.get_full_name() or ticket.created_by.username) if ticket.created_by_id else "-"}\n'
        f'Atribuído a: {(ticket.assigned_to.username if ticket.assigned_to_id else "(ninguém)")}\n\n'
        f'Histórico de comentários:\n' + ('\n'.join(linhas) or '(vazio)') + '\n\n'
        f'Aprendizado (estilo TI):\n{chunks_txt}'
    )


def _executar_tool(ticket_id: int, name: str, args: dict) -> str:
    try:
        if name == 'send_assistente_message':
            return json.dumps(send_assistente_message(ticket_id, args.get('text', '')), ensure_ascii=False)
        if name == 'set_ticket_priority':
            return json.dumps(set_ticket_priority(ticket_id, args.get('priority', '')), ensure_ascii=False)
        if name == 'set_ticket_status':
            return json.dumps(set_ticket_status(ticket_id, args.get('status', '')), ensure_ascii=False)
        if name == 'escalar_para_ti':
            return json.dumps(escalar_para_ti(ticket_id, args.get('motivo', '')), ensure_ascii=False)
        return json.dumps({'ok': False, 'error': f'Tool desconhecida: {name}'})
    except AssistenteServiceError as exc:
        return json.dumps({'ok': False, 'error': str(exc)})


def _parse_args(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def processar_assistente(ticket_id: int) -> None:
    """Processa uma rodada do Assistente no chamado. Seguro para on_commit."""
    try:
        ticket = Ticket.objects.select_related(
            'category', 'created_by', 'assigned_to', 'requester_user',
        ).get(pk=ticket_id)
    except Ticket.DoesNotExist:
        return

    if not assistente_pode_atuar(ticket):
        return

    system = (
        'Você é o Assistente de TI da empresa Money Promotora no helpdesk. '
        'Responda em português, de forma clara e profissional, alinhada ao estilo da equipe de TI. '
        'Tire dúvidas do solicitante. Use as tools para enviar mensagens e, se necessário, '
        'ajustar prioridade/status. Só finalize (RESOLVED) se tiver certeza de que o problema '
        'foi resolvido sem necessidade de técnico. Escale para TI quando precisar de ação humana '
        '(acesso físico, permissões, hardware, etc.). '
        'Sempre envie ao menos uma mensagem via send_assistente_message nesta interação. '
        'Não invente procedimentos internos sem base no histórico.'
    )
    user_msg = (
        'Analise o chamado e aja (tools). Contexto:\n\n' + _montar_contexto(ticket)
    )

    messages: list[dict[str, Any]] = [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': user_msg},
    ]

    enviou_mensagem = False
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            # Revalida a cada round (pode ter escalado)
            ticket.refresh_from_db()
            if not assistente_pode_atuar(ticket) and enviou_mensagem:
                break
            if ticket.assistente_escalado and enviou_mensagem:
                break

            msg = chat_completion(messages, tools=TOOLS_SPEC, temperature=0.35)
            tool_calls = msg.get('tool_calls') or []
            messages.append(msg)

            if not tool_calls:
                # Se veio só texto, publica como mensagem
                content = (msg.get('content') or '').strip()
                if content and not enviou_mensagem:
                    send_assistente_message(ticket_id, content)
                    enviou_mensagem = True
                break

            for call in tool_calls:
                fn = call.get('function') or {}
                name = fn.get('name') or ''
                args = _parse_args(fn.get('arguments'))
                result = _executar_tool(ticket_id, name, args)
                try:
                    parsed = json.loads(result)
                    if name == 'send_assistente_message' and parsed.get('ok'):
                        enviou_mensagem = True
                except json.JSONDecodeError:
                    pass
                messages.append({
                    'role': 'tool',
                    'tool_call_id': call.get('id') or name,
                    'content': result,
                })
        else:
            # max rounds: se ainda não mandou mensagem, tenta texto residual
            pass

        if not enviou_mensagem and assistente_pode_atuar(Ticket.objects.get(pk=ticket_id)):
            # Fallback mínimo
            send_assistente_message(
                ticket_id,
                'Olá! Recebi seu chamado e estou analisando. Em breve retorno com orientações '
                'ou encaminho para a equipe de TI.',
            )
    except (LlmError, AssistenteServiceError, Exception):
        logger.exception('Falha ao processar Assistente no ticket %s', ticket_id)


def gerar_chunks_aprendizado(limite_tickets: int = 30) -> dict:
    """Usa a IA para gerar chunks a partir de chamados finalizados/arquivados."""
    from django.utils import timezone

    from integracoes.llm import chat_text
    from integracoes.models import AssistenteChunk, AssistenteConfig

    tickets = (
        Ticket.objects.filter(Q(status=Ticket.StatusChoices.RESOLVED) | Q(is_archived=True))
        .select_related('category')
        .prefetch_related('comments', 'comments__author')
        .order_by('-resolved_at', '-updated_at')[:limite_tickets]
    )
    if not tickets:
        raise LlmError('Não há chamados resolvidos/arquivados para aprender.')

    blocos = []
    ids = []
    for t in tickets:
        ids.append(t.pk)
        comps = []
        for c in t.comments.filter(is_active=True).order_by('created_at')[:15]:
            if c.is_assistente:
                autor = 'Assistente'
            elif c.author_id:
                autor = c.author.username
            else:
                autor = 'Sistema'
            comps.append(f'  - {autor}: {c.text[:400]}')
        blocos.append(
            f'#{t.pk} [{t.category.name if t.category_id else "-"}] {t.title}\n'
            f'Desc: {t.description[:500]}\nComentários:\n' + '\n'.join(comps)
        )

    prompt = (
        'Com base nos chamados de helpdesk abaixo (já finalizados pela TI real), '
        'gere um JSON array de objetos com chaves: titulo, conteudo, categoria_hint. '
        'Cada item é um "chunk" de aprendizado (tom de resposta, padrões, o que perguntar, '
        'quando escalar). Gere entre 5 e 12 chunks. Responda SOMENTE o JSON.\n\n'
        + '\n\n---\n\n'.join(blocos)
    )
    raw = chat_text([
        {'role': 'system', 'content': 'Você extrai padrões de atendimento de TI. Responda só JSON válido.'},
        {'role': 'user', 'content': prompt},
    ], temperature=0.3)

    match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not match:
        raise LlmError('IA não retornou JSON de chunks.')
    data = json.loads(match.group(0))
    if not isinstance(data, list) or not data:
        raise LlmError('JSON de chunks vazio.')

    AssistenteChunk.objects.all().delete()
    criados = 0
    for item in data:
        if not isinstance(item, dict):
            continue
        titulo = (item.get('titulo') or '').strip()
        conteudo = (item.get('conteudo') or '').strip()
        if not titulo or not conteudo:
            continue
        AssistenteChunk.objects.create(
            titulo=titulo[:200],
            conteudo=conteudo,
            categoria_hint=(item.get('categoria_hint') or '')[:120],
            fonte_ticket_ids=ids,
        )
        criados += 1

    config = AssistenteConfig.get_solo()
    config.ultima_geracao_em = timezone.now()
    config.save(update_fields=['ultima_geracao_em', 'atualizado_em'])
    return {'ok': True, 'chunks': criados, 'tickets_analisados': len(ids)}
