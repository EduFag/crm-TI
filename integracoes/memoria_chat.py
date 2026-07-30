"""Chat de memória/aprendizado: a TI corrige o raciocínio da IA via conversa."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from integracoes.llm import LlmError, chat_completion, chat_text
from integracoes.models import AssistenteChunk, AssistenteMemoriaConversa

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5
SESSION_KEY = 'aprendizado_chat_messages'
SESSION_CONVERSA_ID = 'aprendizado_chat_conversa_id'
ORIENTACAO_PREFIXO = '[ORIENTAÇÃO IA]'

MEMORIA_TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'listar_memorias',
            'description': 'Lista os chunks de aprendizado ativos (id, título, categoria, origem).',
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'gravar_memoria',
            'description': (
                'Grava um novo conhecimento permanente (chunk). '
                'Use quando o usuário pedir para lembrar, gravar na memória ou ensinar um procedimento. '
                'O conteudo deve respeitar as limitações de tools do Assistente '
                '(não gravar "criar chip" — use escalar/mensagem interna à TI).'
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
            'description': (
                'Desativa um chunk incorreto ou obsoleto pelo id (soft-delete). '
                'Não apaga o registro; só remove do contexto do Assistente.'
            ),
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
                'origem': c.origem,
                'ativo': c.ativo,
                'conteudo_preview': c.conteudo[:180],
            }
            for c in AssistenteChunk.objects.filter(ativo=True)[:80]
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
            origem=AssistenteChunk.Origem.CHAT,
            ativo=True,
            tags=[],
        )
        from integracoes.embeddings import atualizar_embedding_chunk
        atualizar_embedding_chunk(chunk)
        return json.dumps({
            'ok': True,
            'chunk_id': chunk.pk,
            'titulo': chunk.titulo,
            'origem': chunk.origem,
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
        # Reativa se estava desligado e a TI corrigiu
        chunk.ativo = True
        chunk.save()
        from integracoes.embeddings import atualizar_embedding_chunk
        atualizar_embedding_chunk(chunk)
        return json.dumps({
            'ok': True,
            'chunk_id': chunk.pk,
            'titulo': chunk.titulo,
            'origem': chunk.origem,
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
        chunk.ativo = False
        chunk.save(update_fields=['ativo', 'atualizado_em'])
        return json.dumps({
            'ok': True,
            'chunk_id': chunk_id,
            'titulo': titulo,
            'acao': 'desativado',
        }, ensure_ascii=False), True

    return json.dumps({'ok': False, 'error': f'tool desconhecida: {name}'}), False


def _system_prompt() -> str:
    resumo = []
    for c in AssistenteChunk.objects.filter(ativo=True)[:40]:
        resumo.append(f'- #{c.pk} [{c.origem}] [{c.categoria_hint or "-"}] {c.titulo}')
    lista = '\n'.join(resumo) or '(nenhuma memória ainda)'
    from integracoes.assistente_limites import prompt_limitacoes_aprendizado

    return (
        'Você é o tutor de aprendizado do Assistente de TI da empresa. '
        'A TI conversa com você para corrigir e enriquecer a memória (chunks) usada no Helpdesk. '
        'Quando o usuário pedir para lembrar, gravar na memória, corrigir um procedimento ou '
        'esquecer algo, use as tools gravar_memoria / atualizar_memoria / remover_memoria. '
        'remover_memoria apenas desativa o chunk (não apaga). '
        'Antes de atualizar/remover, use listar_memorias se precisar do id. '
        'Ao gravar/atualizar, NÃO ensine ações que o Assistente não consegue executar '
        '(ex.: criar chip); reformule para consulta/status + escalar/mensagem interna. '
        'Responda sempre em português, de forma objetiva e legível. '
        'Use Markdown leve (negrito com **, listas numeradas) só quando ajudar a leitura. '
        'Confirme o que foi gravado.\n\n'
        f'{prompt_limitacoes_aprendizado()}\n\n'
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


def _titulo_de_mensagem(texto: str) -> str:
    limpo = (texto or '').strip().replace('\n', ' ')
    if len(limpo) <= 48:
        return limpo or 'Nova conversa'
    return limpo[:45].rstrip() + '…'


def listar_conversas_usuario(user, limite: int = 40) -> list[dict]:
    qs = (
        AssistenteMemoriaConversa.objects.filter(user=user, ativo=True)
        .order_by('-atualizado_em')[: max(1, min(int(limite or 40), 80))]
    )
    return [
        {
            'id': c.pk,
            'titulo': c.titulo or 'Nova conversa',
            'atualizado_em': c.atualizado_em.isoformat() if c.atualizado_em else None,
            'mensagens_count': len(c.mensagens or []),
        }
        for c in qs
    ]


def obter_ou_criar_conversa(user, conversa_id=None) -> AssistenteMemoriaConversa:
    if conversa_id:
        try:
            conv = AssistenteMemoriaConversa.objects.get(
                pk=int(conversa_id), user=user, ativo=True,
            )
            return conv
        except (AssistenteMemoriaConversa.DoesNotExist, TypeError, ValueError):
            pass
    return AssistenteMemoriaConversa.objects.create(
        user=user,
        titulo='Nova conversa',
        mensagens=[],
    )


def processar_mensagem_conversa(user, mensagem_usuario: str, conversa_id=None) -> dict:
    """Processa mensagem, persiste na conversa do usuário e devolve reply + conversa_id."""
    conv = obter_ou_criar_conversa(user, conversa_id)
    historico = list(conv.mensagens or [])
    resultado = processar_mensagem_memoria(historico, mensagem_usuario)
    conv.mensagens = resultado['historico']
    if not conv.titulo or conv.titulo == 'Nova conversa':
        conv.titulo = _titulo_de_mensagem(mensagem_usuario)
    conv.save(update_fields=['mensagens', 'titulo', 'atualizado_em'])
    return {
        **resultado,
        'conversa_id': conv.pk,
        'titulo': conv.titulo,
    }


def aprender_de_orientacao(ticket, texto_dica: str, autor=None) -> dict:
    """Destila orientação da TI + contexto do chamado em chunk permanente (origem=chat)."""
    dica = (texto_dica or '').strip()
    if dica.upper().startswith(ORIENTACAO_PREFIXO):
        dica = dica[len(ORIENTACAO_PREFIXO):].strip()
    if not dica:
        return {'ok': False, 'error': 'Dica vazia.'}

    comps = []
    for c in ticket.comments.filter(is_active=True).order_by('-created_at')[:15]:
        if c.is_assistente:
            autor_txt = 'Assistente'
        elif c.author_id:
            autor_txt = c.author.get_full_name() or c.author.username
        else:
            autor_txt = 'Sistema'
        marca = ' [INTERNO]' if c.is_interno else ''
        comps.append(f'- {autor_txt}{marca}: {(c.text or "")[:350]}')
    comps.reverse()

    from integracoes.assistente_limites import prompt_limitacoes_aprendizado

    prompt = (
        'A TI orientou o Assistente de helpdesk neste chamado. '
        'Gere UM objeto JSON com chaves: titulo, conteudo, categoria_hint, tags (lista). '
        'O chunk deve capturar o procedimento/correção para próximos chamados semelhantes. '
        'Adapte a orientação às limitações de tools do Assistente: se a TI pediu algo '
        'que a IA não executa (ex.: criar/entregar chip), grave o que a IA deve fazer '
        '(consultar/atualizar + mensagem interna + escalar). '
        'conteudo máx. 1000 caracteres.\n\n'
        f'{prompt_limitacoes_aprendizado()}\n\n'
        'Responda SOMENTE o JSON.\n\n'
        f'Chamado #{ticket.pk}: {ticket.title}\n'
        f'Descrição: {(ticket.description or "")[:500]}\n'
        f'Orientação da TI: {dica}\n'
        f'Contexto recente:\n' + ('\n'.join(comps) or '(sem comentários)')
    )
    try:
        raw = chat_text([
            {
                'role': 'system',
                'content': (
                    'Você extrai aprendizado operacional de TI para o Assistente automático. '
                    'Nunca ensine ações fora das tools disponíveis. Responda só JSON válido.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ], temperature=0.2)
    except LlmError as exc:
        logger.warning('aprender_de_orientacao falhou (LLM): %s', exc)
        # Fallback sem LLM: grava a dica crua
        chunk = AssistenteChunk.objects.create(
            titulo=f'Orientação ticket #{ticket.pk}'[:200],
            conteudo=dica[:1200],
            categoria_hint='orientacao',
            fonte_ticket_ids=[ticket.pk],
            origem=AssistenteChunk.Origem.CHAT,
            ativo=True,
            tags=['orientacao'],
        )
        from integracoes.embeddings import atualizar_embedding_chunk
        atualizar_embedding_chunk(chunk)
        return {'ok': True, 'chunk_id': chunk.pk, 'fallback': True}

    match = re.search(r'\{.*\}', raw, re.DOTALL)
    data = {}
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = {}
    titulo = (data.get('titulo') or f'Orientação ticket #{ticket.pk}').strip()[:200]
    conteudo = (data.get('conteudo') or dica).strip()[:1200]
    categoria = (data.get('categoria_hint') or 'orientacao').strip()[:120]
    tags = data.get('tags') if isinstance(data.get('tags'), list) else []
    tags = [str(t).strip()[:40] for t in tags if str(t).strip()][:8]
    if 'orientacao' not in tags:
        tags.insert(0, 'orientacao')

    chunk = AssistenteChunk.objects.create(
        titulo=titulo,
        conteudo=conteudo,
        categoria_hint=categoria,
        fonte_ticket_ids=[ticket.pk],
        origem=AssistenteChunk.Origem.CHAT,
        ativo=True,
        tags=tags,
    )
    from integracoes.embeddings import atualizar_embedding_chunk
    atualizar_embedding_chunk(chunk)
    logger.info(
        'Chunk #%s criado a partir de orientação no ticket #%s (autor=%s)',
        chunk.pk, ticket.pk, getattr(autor, 'pk', None),
    )
    return {'ok': True, 'chunk_id': chunk.pk, 'titulo': chunk.titulo}
