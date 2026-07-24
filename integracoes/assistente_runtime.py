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
    consultar_acesso_discador,
    consultar_chips,
    consultar_licencas_discador,
    consultar_usuario,
    criar_acesso_discador,
    descrever_imagem_anexo,
    escalar_para_ti,
    liberar_acesso_discador,
    liberar_licenca_ramal,
    listar_anexos_ticket,
    listar_campanhas_discador,
    listar_categorias_especificas,
    listar_ramais_discador,
    recusar_chamado,
    send_assistente_message,
    set_ticket_priority,
    set_ticket_status,
    triar_chamado,
)
from helpdesk.models import Comment, Ticket
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
                'Envia uma mensagem CURTA ao solicitante (1–3 frases). '
                'Chame de novo para a próxima fala — prefira 2–4 bolhas em vez de um texto longo. '
                'Use Markdown leve (**negrito**, listas).'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'text': {
                        'type': 'string',
                        'description': 'Texto curto em português (Markdown leve ok).',
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
            'description': 'Lista anexos do chamado e dos comentários (refs para ler_imagem_anexo).',
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'ler_imagem_anexo',
            'description': (
                'Lê/descreve uma imagem anexada (print). Use ref de listar_anexos '
                '(ticket:ID ou comment:ID). Se falhar, peça ao usuário descrever o print.'
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
            'name': 'consultar_chips',
            'description': (
                'Consulta chips WhatsApp por nome do consultor ou número da linha. '
                'Use antes de orientar ativação de chip novo (verificar quantos já tem).'
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
            'name': 'consultar_usuario',
            'description': 'Busca usuário no CRM (acessos) por username ou nome.',
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
            'name': 'consultar_licencas_discador',
            'description': (
                'Consulta licenças do discador (JoyTec): contratadas, ramais livres (FREE), '
                'em uso, slots disponíveis no contrato. Use em pedidos de ramal/campanha.'
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
            'description': 'Lista ramais do discador. Filtre status FREE|IN_USE|NOT_CONFIGURED.',
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
            'description': 'Busca acesso no discador por titular, login ou número do ramal.',
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
            'description': 'Lista campanhas ativas do discador (id e nome).',
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
            'name': 'criar_acesso_discador',
            'description': (
                'Cria acesso no discador (titular + login + campanha). '
                'Se omitir ramal, usa um FREE. Consulte licenças antes.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'titular_nome': {'type': 'string'},
                    'login_discador': {'type': 'string'},
                    'tipo': {
                        'type': 'string',
                        'enum': ['CONSULTOR', 'VENDEDOR', 'NEGOCIADOR'],
                    },
                    'ramal_numero': {'type': 'string'},
                    'ramal_id': {'type': 'integer'},
                    'campanha_nome': {'type': 'string'},
                    'campanha_id': {'type': 'integer'},
                    'slug': {'type': 'string'},
                },
                'required': ['titular_nome', 'login_discador'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'liberar_acesso_discador',
            'description': 'Remove acesso (ramal fica FREE; ainda consome licença). Use acesso_id de consultar_acesso_discador.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'acesso_id': {'type': 'integer'},
                },
                'required': ['acesso_id'],
            },
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'liberar_licenca_ramal',
            'description': (
                'Marca ramal como NOT_CONFIGURED (libera slot do contrato). '
                'Só se não houver acesso — liberar_acesso_discador antes se precisar.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'ramal_id': {'type': 'integer'},
                    'ramal_numero': {'type': 'string'},
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
                'Encerra o Assistente e pede técnico de TI. Use para MoneyConsig, AnyDesk, '
                'hardware, permissões ou quando o discador estiver no limite e precisar '
                'aumentar contrato.'
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
        tipo = 'imagem' if a.get('is_image') else 'arquivo'
        linhas.append(f"- {a.get('ref')} [{tipo}] {a.get('nome')}")
    return '\n'.join(linhas)


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
        extra = ' [tem anexo]' if c.attachment else ''
        linhas.append(f'[{autor}]{extra} {c.text}')

    chunks = _chunks_relevantes(ticket)
    chunks_txt = '\n'.join(f'- {ch.titulo}: {ch.conteudo}' for ch in chunks) or '(sem chunks ainda)'
    cat_esp = ticket.specific_category.name if ticket.specific_category_id else '(não triado)'

    return (
        f'Chamado #{ticket.pk}\n'
        f'Título: {ticket.title}\n'
        f'Descrição: {ticket.description}\n'
        f'Status: {ticket.status}\n'
        f'Prioridade: {ticket.priority or "(não definida)"}\n'
        f'Categoria: {ticket.category.name if ticket.category_id else "-"}\n'
        f'Categoria específica: {cat_esp}\n'
        f'Solicitante: {ticket.requester_name}\n'
        f'Criador: {(ticket.created_by.get_full_name() or ticket.created_by.username) if ticket.created_by_id else "-"}\n'
        f'Atribuído a: {(ticket.assigned_to.username if ticket.assigned_to_id else "(ninguém)")}\n\n'
        f'Anexos:\n{_resumo_anexos(ticket)}\n\n'
        f'Histórico de comentários:\n' + ('\n'.join(linhas) or '(vazio)') + '\n\n'
        f'Aprendizado (estilo TI / chunks):\n{chunks_txt}'
    )


def _system_prompt() -> str:
    return (
        'Você é o Assistente de TI da Money Promotora no helpdesk. '
        'Responda em português, claro e profissional, alinhado aos chunks de aprendizado.\n\n'
        'Formato das mensagens:\n'
        '- Use Markdown leve (**negrito**, listas com - ou 1.).\n'
        '- Envie 2–4 mensagens curtas via send_assistente_message (1–3 frases cada). '
        'Nunca um único bloco longo.\n\n'
        'Procedimentos:\n'
        '- Siga os chunks (discador, acessos, WhatsApp, etc.).\n'
        '- Se o procedimento pedir print/números e não houver anexo, peça via mensagem.\n'
        '- Se houver anexos de imagem, use listar_anexos e ler_imagem_anexo ANTES de decidir.\n'
        '- TRIAGEM OBRIGATÓRIA: se Prioridade estiver "(não definida)", nesta interação '
        'chame listar_categorias_especificas (se precisar do id) e triar_chamado '
        'ANTES ou JUNTO das mensagens ao solicitante.\n'
        '- WhatsApp/chip: consulte consultar_chips pelo nome do consultor; se já tiver 2 em uso, questione.\n'
        '- Discador/JoyTec: use consultar_licencas_discador e listar_ramais_discador (FREE); '
        'consultar_acesso_discador para achar titular; criar_acesso_discador / '
        'liberar_acesso_discador / liberar_licenca_ramal conforme o caso. '
        'Se no_limite/estourado e precisar de slot novo, explique e escalar_para_ti.\n'
        '- Acesso CRM: pergunte qual sistema; use consultar_usuario para caso individual.\n'
        '- Título/descrição incorretos: recusar_chamado com motivo (não invente o problema).\n'
        '- Ações externas (MoneyConsig, AnyDesk, hardware, permissões fora do CRM/discador): '
        'oriente conforme o chunk e escalar_para_ti com motivo.\n'
        '- Só use RESOLVED se o problema foi resolvido sem TI (recusa usa recusar_chamado).\n'
        '- Sempre envie ao menos uma mensagem via send_assistente_message nesta interação.\n'
        '- Não invente procedimentos fora dos chunks e do histórico.'
    )


def _executar_tool(ticket_id: int, name: str, args: dict) -> str:
    try:
        if name == 'send_assistente_message':
            return json.dumps(send_assistente_message(ticket_id, args.get('text', '')), ensure_ascii=False)
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
        if name == 'consultar_chips':
            return json.dumps(consultar_chips(args.get('q', '')), ensure_ascii=False)
        if name == 'consultar_usuario':
            return json.dumps(consultar_usuario(args.get('q', '')), ensure_ascii=False)
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
        if name == 'criar_acesso_discador':
            return json.dumps(
                criar_acesso_discador(
                    args.get('titular_nome', ''),
                    args.get('login_discador', ''),
                    args.get('tipo') or 'CONSULTOR',
                    args.get('ramal_id'),
                    args.get('ramal_numero') or '',
                    args.get('campanha_id'),
                    args.get('campanha_nome') or '',
                    args.get('slug') or 'joytec',
                ),
                ensure_ascii=False,
            )
        if name == 'liberar_acesso_discador':
            return json.dumps(
                liberar_acesso_discador(int(args.get('acesso_id') or 0)),
                ensure_ascii=False,
            )
        if name == 'liberar_licenca_ramal':
            return json.dumps(
                liberar_licenca_ramal(
                    args.get('ramal_id'),
                    args.get('ramal_numero') or '',
                    args.get('slug') or 'joytec',
                ),
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
    if ticket.assistente_escalado and enviou_mensagem:
        return enviou_mensagem
    if ticket.is_rejected and enviou_mensagem:
        return enviou_mensagem

    msg = chat_completion(messages, tools=TOOLS_SPEC, temperature=0.35)
    tool_calls = msg.get('tool_calls') or []
    messages.append(msg)

    if not tool_calls:
        content = (msg.get('content') or '').strip()
        if content and not enviou_mensagem:
            send_assistente_message(ticket_id, content)
            enviou_mensagem = True
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


def processar_assistente(ticket_id: int) -> None:
    """Processa uma rodada do Assistente no chamado. Seguro para on_commit/thread."""
    try:
        ticket = Ticket.objects.select_related(
            'category', 'specific_category', 'created_by', 'assigned_to', 'requester_user',
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

    messages: list[dict[str, Any]] = [
        {'role': 'system', 'content': _system_prompt()},
        {
            'role': 'user',
            'content': 'Analise o chamado e aja (tools). Contexto:\n\n' + _montar_contexto(ticket),
        },
    ]

    enviou_mensagem = False
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            ticket.refresh_from_db()
            if not assistente_pode_atuar(ticket) and enviou_mensagem:
                break
            if ticket.assistente_escalado and enviou_mensagem:
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

        if not enviou_mensagem and assistente_pode_atuar(Ticket.objects.get(pk=ticket_id)):
            send_assistente_message(ticket_id, _MSG_FALLBACK)
            enviou_mensagem = True

        _garantir_triagem(ticket_id, messages)
    except (LlmError, AssistenteServiceError, Exception):
        logger.exception('Falha ao processar Assistente no ticket %s', ticket_id)
        # Best-effort: chamado não fica mudo se o LLM falhar
        try:
            if not enviou_mensagem and assistente_pode_atuar(
                Ticket.objects.get(pk=ticket_id),
            ):
                send_assistente_message(ticket_id, _MSG_FALLBACK_ERRO)
        except Exception:
            logger.exception(
                'Falha ao enviar fallback do Assistente no ticket %s',
                ticket_id,
            )
        try:
            _garantir_triagem(ticket_id, messages)
        except Exception:
            pass


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
