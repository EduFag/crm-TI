"""Chat de memória/aprendizado: a TI corrige o raciocínio da IA via conversa."""

from __future__ import annotations

import json
import logging
from typing import Any

from integracoes.llm import LlmError, chat_completion
from integracoes.models import AssistenteChunk

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5
SESSION_KEY = 'aprendizado_chat_messages'

MEMORIA_TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'listar_memorias',
            'description': 'Lista os chunks de aprendizado atuais (id, título, categoria).',
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'gravar_memoria',
            'description': (
                'Grava um novo conhecimento permanente (chunk). '
                'Use quando o usuário pedir para lembrar, gravar na memória ou ensinar um procedimento.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'titulo': {'type': 'string'},
                    'conteudo': {'type': 'string'},
                    'categoria_hint': {'type': 'string'},
                },
                'required': ['titulo', 'conteudo'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'atualizar_memoria',
            'description': 'Corrige um chunk existente pelo id.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'chunk_id': {'type': 'integer'},
                    'titulo': {'type': 'string'},
                    'conteudo': {'type': 'string'},
                    'categoria_hint': {'type': 'string'},
                },
                'required': ['chunk_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'remover_memoria',
            'description': 'Remove um chunk incorreto ou obsoleto pelo id.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'chunk_id': {'type': 'integer'},
                },
                'required': ['chunk_id'],
            },
        },
    },
]


def _parse_args(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _executar_tool(name: str, args: dict) -> tuple[str, bool]:
    """Retorna (json_resultado, memoria_alterada)."""
    if name == 'listar_memorias':
        itens = [
            {
                'id': c.pk,
                'titulo': c.titulo,
                'categoria_hint': c.categoria_hint,
                'conteudo_preview': c.conteudo[:180],
            }
            for c in AssistenteChunk.objects.all()[:80]
        ]
        return json.dumps({'ok': True, 'chunks': itens}, ensure_ascii=False), False

    if name == 'gravar_memoria':
        titulo = (args.get('titulo') or '').strip()
        conteudo = (args.get('conteudo') or '').strip()
        categoria = (args.get('categoria_hint') or '').strip()
        if not titulo or not conteudo:
            return json.dumps({'ok': False, 'error': 'titulo e conteudo obrigatórios'}), False
        chunk = AssistenteChunk.objects.create(
            titulo=titulo[:200],
            conteudo=conteudo,
            categoria_hint=categoria[:120],
            fonte_ticket_ids=[],
        )
        return json.dumps({
            'ok': True,
            'chunk_id': chunk.pk,
            'titulo': chunk.titulo,
            'acao': 'criado',
        }, ensure_ascii=False), True

    if name == 'atualizar_memoria':
        chunk_id = args.get('chunk_id')
        try:
            chunk_id = int(chunk_id)
        except (TypeError, ValueError):
            return json.dumps({'ok': False, 'error': 'chunk_id inválido'}), False
        chunk = AssistenteChunk.objects.filter(pk=chunk_id).first()
        if not chunk:
            return json.dumps({'ok': False, 'error': 'chunk não encontrado'}), False
        if args.get('titulo'):
            chunk.titulo = str(args['titulo']).strip()[:200]
        if args.get('conteudo'):
            chunk.conteudo = str(args['conteudo']).strip()
        if 'categoria_hint' in args and args.get('categoria_hint') is not None:
            chunk.categoria_hint = str(args.get('categoria_hint') or '').strip()[:120]
        chunk.save()
        return json.dumps({
            'ok': True,
            'chunk_id': chunk.pk,
            'titulo': chunk.titulo,
            'acao': 'atualizado',
        }, ensure_ascii=False), True

    if name == 'remover_memoria':
        chunk_id = args.get('chunk_id')
        try:
            chunk_id = int(chunk_id)
        except (TypeError, ValueError):
            return json.dumps({'ok': False, 'error': 'chunk_id inválido'}), False
        chunk = AssistenteChunk.objects.filter(pk=chunk_id).first()
        if not chunk:
            return json.dumps({'ok': False, 'error': 'chunk não encontrado'}), False
        titulo = chunk.titulo
        chunk.delete()
        return json.dumps({
            'ok': True,
            'chunk_id': chunk_id,
            'titulo': titulo,
            'acao': 'removido',
        }, ensure_ascii=False), True

    return json.dumps({'ok': False, 'error': f'tool desconhecida: {name}'}), False


def _system_prompt() -> str:
    resumo = []
    for c in AssistenteChunk.objects.all()[:40]:
        resumo.append(f'- #{c.pk} [{c.categoria_hint or "-"}] {c.titulo}')
    lista = '\n'.join(resumo) or '(nenhuma memória ainda)'
    return (
        'Você é o tutor de aprendizado do Assistente de TI da empresa. '
        'A TI conversa com você para corrigir e enriquecer a memória (chunks) usada no Helpdesk. '
        'Quando o usuário pedir para lembrar, gravar na memória, corrigir um procedimento ou '
        'esquecer algo, use as tools gravar_memoria / atualizar_memoria / remover_memoria. '
        'Antes de atualizar/remover, use listar_memorias se precisar do id. '
        'Responda sempre em português, de forma objetiva. Confirme o que foi gravado.\n\n'
        f'Memórias atuais:\n{lista}'
    )


def processar_mensagem_memoria(historico: list[dict], mensagem_usuario: str) -> dict:
    """
    Processa uma mensagem do chat de memória.
    historico: lista de {role, content} anteriores (sem system).
    Retorna {reply, historico, memoria_alterada}.
    """
    texto = (mensagem_usuario or '').strip()
    if not texto:
        raise LlmError('Mensagem vazia.')

    messages: list[dict[str, Any]] = [{'role': 'system', 'content': _system_prompt()}]
    for item in historico[-20:]:
        role = item.get('role')
        content = item.get('content')
        if role in ('user', 'assistant') and content:
            messages.append({'role': role, 'content': content})
    messages.append({'role': 'user', 'content': texto})

    memoria_alterada = False
    resposta_final = ''

    for _ in range(MAX_ROUNDS):
        msg = chat_completion(messages, tools=MEMORIA_TOOLS, temperature=0.3)
        tool_calls = msg.get('tool_calls') or []
        messages.append(msg)

        if not tool_calls:
            resposta_final = (msg.get('content') or '').strip()
            break

        for call in tool_calls:
            fn = call.get('function') or {}
            name = fn.get('name') or ''
            args = _parse_args(fn.get('arguments'))
            result, alterou = _executar_tool(name, args)
            if alterou:
                memoria_alterada = True
            messages.append({
                'role': 'tool',
                'tool_call_id': call.get('id') or name,
                'content': result,
            })
    else:
        resposta_final = (messages[-1].get('content') or '').strip() if isinstance(messages[-1], dict) else ''

    if not resposta_final:
        resposta_final = (
            'Pronto. Atualizei a memória conforme solicitado.'
            if memoria_alterada
            else 'Não consegui processar. Tente reformular o pedido.'
        )

    novo_historico = list(historico[-18:])
    novo_historico.append({'role': 'user', 'content': texto})
    novo_historico.append({'role': 'assistant', 'content': resposta_final})

    return {
        'reply': resposta_final,
        'historico': novo_historico,
        'memoria_alterada': memoria_alterada,
    }
