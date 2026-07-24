"""Serviços de escrita/leitura do Assistente (MCP e runtime Django)."""

from __future__ import annotations

import logging
import mimetypes
import os
import re
from typing import Any

from django.db.models import Q
from django.utils import timezone

from helpdesk.models import Comment, Ticket, TicketAttachment, TicketSpecificCategory
from helpdesk.ticket_access import usuario_eh_operador_helpdesk


logger = logging.getLogger(__name__)

PRIORIDADES = {c.value for c in Ticket.PriorityChoices}
STATUS_VALIDOS = {c.value for c in Ticket.StatusChoices}


class AssistenteServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


def ticket_assumido_pela_ti(ticket: Ticket) -> bool:
    """
    TI assume o atendimento quando há técnico e o chamado NÃO está em Novos.
    Voltar para Novos (mesmo com assigned_to residual) libera o Assistente.
    """
    if ticket.status == Ticket.StatusChoices.NEW:
        return False
    return usuario_eh_operador_helpdesk(ticket.assigned_to)


def assistente_motivo_bloqueio(ticket: Ticket) -> str | None:
    """Retorna o motivo se o Assistente não pode atuar; None se pode."""
    from integracoes.models import AssistenteConfig

    config = AssistenteConfig.get_solo()
    if not config.ativo:
        return 'assistente_inativo'
    if not ticket.is_active or ticket.is_archived:
        return 'ticket_inativo_ou_arquivado'
    if ticket.status == Ticket.StatusChoices.RESOLVED:
        return 'ticket_resolvido'
    if ticket.assistente_escalado:
        return 'assistente_escalado'
    if ticket_assumido_pela_ti(ticket):
        return 'assumido_pela_ti'
    # Bloqueia só chamado interno: solicitante vinculado é operador TI
    if ticket.requester_user_id and usuario_eh_operador_helpdesk(ticket.requester_user):
        return 'solicitante_eh_operador_ti'
    return None


def assistente_pode_atuar(ticket: Ticket) -> bool:
    """Regras para o Assistente continuar conversando no chamado."""
    return assistente_motivo_bloqueio(ticket) is None


_MAX_CHARS_BOLHA = 350

# Rótulos meta que a IA às vezes coloca no texto (não devem ir ao solicitante)
_RE_ROTULO_MENSAGEM = re.compile(
    r'(?im)(?:^|\n)\s*\*{0,2}\s*(?:\d+[ªºa]?\.?\s*)?mensagem(?:\s*\d+)?\s*:?\s*\*{0,2}\s*',
)
_RE_LINHA_PENSAMENTO = re.compile(
    r'(?i)^\s*(?:'
    r'ok[,.]?\s+.+|'
    r'vou\s+\w+.*|'
    r'sem\s+chips?\s+ainda.*|'
    r'(?:pensamento|racioc[ií]nio|nota\s+interna|plano(?:\s+de\s+a[cç][aã]o)?)\s*:?\s*.*|'
    r'analisando(?:\s+o)?\s+chamado.*|'
    r'agora\s+vou\s+.*|'
    r'primeiro\s+vou\s+.*|'
    r'deixa\s+eu\s+.*|'
    r'certo[,.]?\s+vou\s+.*'
    r')\s*$'
)


def limpar_texto_para_solicitante(texto: str) -> str:
    """
    Remove raciocínio/meta da IA, deixando só a fala ao solicitante.
    Ex.: remove 'Ok, vou...' e rótulos '**1ª mensagem:**'.
    """
    texto = (texto or '').replace('\r\n', '\n').replace('\r', '\n').strip()
    if not texto:
        return ''

    # Se há "1ª mensagem:" / "**2ª mensagem:**", descarta o preâmbulo e junta os corpos
    if _RE_ROTULO_MENSAGEM.search(texto):
        partes = _RE_ROTULO_MENSAGEM.split(texto)
        corpos = [p.strip() for p in partes[1:] if p and p.strip()]
        if corpos:
            texto = '\n\n'.join(corpos)
        else:
            # só rótulo sem corpo
            texto = _RE_ROTULO_MENSAGEM.sub('', texto).strip()

    # Remove linhas de pensamento no início (e linhas em branco extras)
    linhas = texto.split('\n')
    while linhas:
        primeira = linhas[0].strip()
        if not primeira:
            linhas.pop(0)
            continue
        if _RE_LINHA_PENSAMENTO.match(primeira):
            linhas.pop(0)
            continue
        break

    # Remove linhas que são só rótulo residual no meio
    limpas = []
    for ln in linhas:
        s = ln.strip()
        if re.match(r'(?i)^\*{0,2}\s*(?:\d+[ªºa]?\.?\s*)?mensagem(?:\s*\d+)?\s*:?\s*\*{0,2}$', s):
            continue
        limpas.append(ln)

    return '\n'.join(limpas).strip()


def _partir_texto_assistente(texto: str, max_chars: int = _MAX_CHARS_BOLHA) -> list[str]:
    """Parte texto longo em várias bolhas (parágrafos / pedaços ~max_chars)."""
    texto = (texto or '').replace('\r\n', '\n').replace('\r', '\n').strip()
    if not texto:
        return []

    # Parágrafos separados por linha em branco
    paragrafos = [p.strip() for p in texto.split('\n\n') if p.strip()]
    if len(paragrafos) <= 1 and len(texto) <= max_chars:
        return [texto]

    if len(paragrafos) <= 1:
        # Um bloco longo: quebra por linhas ou por tamanho
        linhas = [ln.strip() for ln in texto.split('\n') if ln.strip()]
        paragrafos = linhas if len(linhas) > 1 else [texto]

    partes: list[str] = []
    atual = ''
    for trecho in paragrafos:
        if len(trecho) > max_chars:
            if atual:
                partes.append(atual)
                atual = ''
            # Pedacos forçados por tamanho
            resto = trecho
            while len(resto) > max_chars:
                corte = resto.rfind(' ', 0, max_chars + 1)
                if corte < max_chars // 2:
                    corte = max_chars
                partes.append(resto[:corte].strip())
                resto = resto[corte:].strip()
            if resto:
                atual = resto
            continue
        candidato = f'{atual}\n\n{trecho}'.strip() if atual else trecho
        if atual and len(candidato) > max_chars:
            partes.append(atual)
            atual = trecho
        else:
            atual = candidato
    if atual:
        partes.append(atual)
    return partes or [texto]


def _notificar_comentario_assistente(ticket: Ticket, texto: str) -> None:
    """Audit + badge + push para comentário do Assistente (uma vez por lote)."""
    preview = (texto or '')[:120]
    try:
        from helpdesk.audit import log_comentario
        log_comentario(ticket, None, preview, metadata={'is_assistente': True})
    except Exception:
        pass
    try:
        from helpdesk.views.kanban import adicionar_nao_lido
        adicionar_nao_lido(ticket, None)
    except Exception:
        pass
    try:
        from helpdesk.notifications import EVENTO_COMMENT, agendar_notificacao_chamado
        agendar_notificacao_chamado(ticket, None, EVENTO_COMMENT, preview)
    except Exception:
        pass


def send_assistente_message(ticket_id: int, text: str) -> dict:
    # Remove pensamento/meta da IA antes de gravar no chamado
    texto = limpar_texto_para_solicitante(text)
    if not texto:
        raise AssistenteServiceError(
            'Texto do comentário é obrigatório '
            '(após remover raciocínio interno não restou mensagem ao solicitante).'
        )
    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)

    pedacos = _partir_texto_assistente(texto)
    comment_ids: list[int] = []
    for pedaco in pedacos:
        comment = Comment.objects.create(
            ticket=ticket,
            author=None,
            text=pedaco,
            is_assistente=True,
        )
        comment_ids.append(comment.pk)

    ticket.updated_at = timezone.now()
    ticket.save(update_fields=['updated_at'])
    # Uma notificação por lote (evita spam se partiu em várias bolhas)
    _notificar_comentario_assistente(ticket, pedacos[0] if pedacos else texto)

    return {
        'ok': True,
        'comment_id': comment_ids[0] if comment_ids else None,
        'comment_ids': comment_ids,
        'ticket_id': ticket.pk,
        'text': pedacos[0] if len(pedacos) == 1 else '\n\n'.join(pedacos),
        'bolhas': len(pedacos),
    }


def set_ticket_priority(ticket_id: int, priority: str) -> dict:
    priority = (priority or '').strip().upper()
    if priority not in PRIORIDADES:
        raise AssistenteServiceError(f'Prioridade inválida. Use: {", ".join(sorted(PRIORIDADES))}.')
    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    antes = ticket.priority
    ticket.priority = priority
    ticket.save(update_fields=['priority', 'updated_at'])
    try:
        from helpdesk.audit import log_prioridade_alterada
        log_prioridade_alterada(ticket, None, antes, priority)
    except Exception:
        pass
    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'priority_antes': antes,
        'priority': ticket.priority,
    }


def set_ticket_status(ticket_id: int, status: str) -> dict:
    status = (status or '').strip().upper()
    if status not in STATUS_VALIDOS:
        raise AssistenteServiceError(f'Status inválido. Use: {", ".join(sorted(STATUS_VALIDOS))}.')
    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    antes = ticket.status
    ticket.status = status
    update_fields = ['status', 'updated_at']
    if status == Ticket.StatusChoices.RESOLVED and not ticket.resolved_at:
        ticket.resolved_at = timezone.now()
        update_fields.append('resolved_at')
    ticket.save(update_fields=update_fields)
    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'status_antes': antes,
        'status': ticket.status,
    }


def escalar_para_ti(ticket_id: int, motivo: str = '') -> dict:
    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    ticket.assistente_escalado = True
    update_fields = ['assistente_escalado', 'updated_at']
    if ticket.status == Ticket.StatusChoices.NEW:
        ticket.status = Ticket.StatusChoices.PENDING
        update_fields.append('status')
    ticket.save(update_fields=update_fields)

    motivo_limpo = (motivo or '').strip()
    texto = (
        'Encaminhei este chamado para a equipe de TI analisar. '
        'Um técnico assumirá o atendimento em breve.'
    )
    if motivo_limpo:
        texto = f'{texto}\n\nMotivo: {motivo_limpo}'
    comment = Comment.objects.create(
        ticket=ticket,
        author=None,
        text=texto,
        is_assistente=True,
    )
    _notificar_comentario_assistente(ticket, texto)
    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'assistente_escalado': True,
        'status': ticket.status,
        'comment_id': comment.pk,
    }


def listar_categorias_especificas() -> dict:
    cats = list(
        TicketSpecificCategory.objects.filter(is_active=True)
        .order_by('name')
        .values('id', 'name')
    )
    return {'ok': True, 'count': len(cats), 'results': list(cats)}


def triar_chamado(
    ticket_id: int,
    priority: str,
    specific_category_id: int | None = None,
) -> dict:
    """Define prioridade e categoria específica (triagem), sem forçar mudança de coluna."""
    priority = (priority or '').strip().upper()
    if priority not in PRIORIDADES:
        raise AssistenteServiceError(f'Prioridade inválida. Use: {", ".join(sorted(PRIORIDADES))}.')

    ticket = Ticket.objects.select_related('specific_category').filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    if ticket.status == Ticket.StatusChoices.RESOLVED:
        raise AssistenteServiceError('Não é possível triar chamado resolvido.')

    cat_id = specific_category_id
    if cat_id is not None and cat_id != '':
        try:
            cat_id = int(cat_id)
        except (TypeError, ValueError):
            raise AssistenteServiceError('specific_category_id inválido.')
        if not TicketSpecificCategory.objects.filter(pk=cat_id, is_active=True).exists():
            raise AssistenteServiceError('Categoria específica não encontrada ou inativa.', 404)
    else:
        cat_id = None

    prioridade_antes = ticket.priority
    cat_antes = ticket.specific_category
    ticket.priority = priority
    ticket.specific_category_id = cat_id
    ticket.save(update_fields=['priority', 'specific_category', 'updated_at'])
    ticket.refresh_from_db()

    try:
        from helpdesk.audit import log_prioridade_alterada, log_triagem_alterada
        if prioridade_antes != priority:
            log_prioridade_alterada(ticket, None, prioridade_antes, priority)
        if (cat_antes.pk if cat_antes else None) != ticket.specific_category_id:
            log_triagem_alterada(ticket, None, cat_antes, ticket.specific_category)
    except Exception:
        pass

    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'priority': ticket.priority,
        'specific_category_id': ticket.specific_category_id,
        'specific_category': ticket.specific_category.name if ticket.specific_category_id else None,
        'status': ticket.status,
    }


def recusar_chamado(ticket_id: int, motivo: str) -> dict:
    """Recusa o chamado (título/descrição incorretos etc.) e encerra o Assistente."""
    motivo_limpo = (motivo or '').strip()
    if not motivo_limpo:
        raise AssistenteServiceError('Motivo da recusa é obrigatório.')

    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    if ticket.status == Ticket.StatusChoices.RESOLVED and ticket.is_rejected:
        raise AssistenteServiceError('Chamado já está recusado.')

    ticket.status = Ticket.StatusChoices.RESOLVED
    ticket.is_rejected = True
    ticket.rejection_reason = motivo_limpo
    ticket.assistente_escalado = True
    if not ticket.resolved_at:
        ticket.resolved_at = timezone.now()
    ticket.save(update_fields=[
        'status', 'is_rejected', 'rejection_reason', 'assistente_escalado',
        'resolved_at', 'updated_at',
    ])

    texto = (
        f'Chamado recusado.\nMotivo: {motivo_limpo}\n\n'
        'Por favor, abra um novo chamado com título e descrição que correspondam '
        'ao problema real.'
    )
    comment = Comment.objects.create(
        ticket=ticket,
        author=None,
        text=texto,
        is_assistente=True,
    )
    _notificar_comentario_assistente(ticket, texto)
    try:
        from helpdesk.audit import log_chamado_recusado
        log_chamado_recusado(ticket, None, motivo_limpo)
    except Exception:
        pass

    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'is_rejected': True,
        'status': ticket.status,
        'comment_id': comment.pk,
        'motivo': motivo_limpo,
    }


def _mime_e_ext(nome: str, content_type: str | None = None) -> tuple[str, str]:
    ext = os.path.splitext(nome or '')[1].lower()
    mime = (content_type or '').split(';')[0].strip().lower()
    # Mapeia extensão → mime (Windows às vezes não conhece webp)
    por_ext = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.pdf': 'application/pdf',
    }
    if ext in por_ext:
        mime = por_ext[ext]
    elif not mime or mime == 'application/octet-stream':
        guessed, _ = mimetypes.guess_type(nome or '')
        mime = (guessed or 'application/octet-stream').split(';')[0].strip().lower()
    return mime, ext


def _eh_imagem(ext: str, mime: str) -> bool:
    return ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'] or (
        mime or ''
    ).startswith('image/')


def _eh_pdf(ext: str, mime: str) -> bool:
    return ext == '.pdf' or (mime or '') == 'application/pdf'


def _normalizar_imagem_para_visao(raw: bytes, mime: str, ext: str) -> tuple[bytes, str]:
    """
    Converte qualquer formato (webp/png/gif/bmp) para JPEG RGB e reduz se grande.
    APIs de visão costumam falhar com webp ou mime octet-stream.
    """
    import io

    from PIL import Image

    try:
        img = Image.open(io.BytesIO(raw))
        if getattr(img, 'n_frames', 1) > 1:
            img.seek(0)
        img = img.convert('RGB')
        # Limita dimensão para caber no payload e acelerar OCR
        max_lado = 1600
        w, h = img.size
        if max(w, h) > max_lado:
            img.thumbnail((max_lado, max_lado), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=85, optimize=True)
        return buf.getvalue(), 'image/jpeg'
    except Exception as exc:
        # Se Pillow falhar e já for jpeg/png reconhecido, devolve original
        if mime in ('image/jpeg', 'image/png') and raw:
            return raw, mime
        raise AssistenteServiceError(
            f'Não foi possível processar a imagem ({ext or mime}): {exc}'
        ) from exc


def listar_anexos_ticket(ticket_id: int) -> dict:
    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)

    resultados: list[dict[str, Any]] = []
    for att in ticket.attachments.all().order_by('created_at'):
        mime, ext = _mime_e_ext(att.file_name or att.file.name)
        resultados.append({
            'ref': f'ticket:{att.pk}',
            'origem': 'ticket',
            'id': att.pk,
            'nome': att.file_name or os.path.basename(att.file.name),
            'ext': ext,
            'mime': mime,
            'is_image': _eh_imagem(ext, mime),
            'is_pdf': _eh_pdf(ext, mime),
            'url': att.file.url if att.file else None,
        })

    for c in (
        Comment.objects.filter(ticket=ticket, is_active=True)
        .exclude(attachment='')
        .exclude(attachment=None)
        .order_by('created_at')
    ):
        if not c.attachment:
            continue
        nome = os.path.basename(c.attachment.name)
        mime, ext = _mime_e_ext(nome)
        resultados.append({
            'ref': f'comment:{c.pk}',
            'origem': 'comment',
            'id': c.pk,
            'nome': nome,
            'ext': ext,
            'mime': mime,
            'is_image': c.is_image if hasattr(c, 'is_image') else _eh_imagem(ext, mime),
            'is_pdf': _eh_pdf(ext, mime),
            'url': c.attachment.url,
            'comment_id': c.pk,
        })

    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'count': len(resultados),
        'results': resultados,
    }


def _resolver_anexo(ticket_id: int, attachment_ref: str):
    """Retorna (file_field, nome, mime) ou levanta AssistenteServiceError."""
    ref = (attachment_ref or '').strip()
    if not ref:
        raise AssistenteServiceError('Informe attachment_ref (ex.: ticket:12 ou comment:34).')

    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)

    if ref.startswith('ticket:'):
        try:
            pk = int(ref.split(':', 1)[1])
        except ValueError:
            raise AssistenteServiceError('attachment_ref inválido.')
        att = TicketAttachment.objects.filter(pk=pk, ticket_id=ticket_id).first()
        if not att or not att.file:
            raise AssistenteServiceError('Anexo do ticket não encontrado.', 404)
        nome = att.file_name or os.path.basename(att.file.name)
        mime, ext = _mime_e_ext(nome)
        return att.file, nome, mime, ext

    if ref.startswith('comment:'):
        try:
            pk = int(ref.split(':', 1)[1])
        except ValueError:
            raise AssistenteServiceError('attachment_ref inválido.')
        comment = Comment.objects.filter(pk=pk, ticket_id=ticket_id, is_active=True).first()
        if not comment or not comment.attachment:
            raise AssistenteServiceError('Anexo do comentário não encontrado.', 404)
        nome = os.path.basename(comment.attachment.name)
        mime, ext = _mime_e_ext(nome)
        return comment.attachment, nome, mime, ext

    # Compat: só número → tenta ticket attachment
    if ref.isdigit():
        return _resolver_anexo(ticket_id, f'ticket:{ref}')

    raise AssistenteServiceError('attachment_ref deve ser ticket:<id> ou comment:<id>.')


def _ler_bytes_anexo(file_field) -> bytes:
    try:
        file_field.open('rb')
        return file_field.read()
    finally:
        try:
            file_field.close()
        except Exception:
            pass


def descrever_imagem_anexo(ticket_id: int, attachment_ref: str) -> dict:
    """
    Lê imagem: tenta visão multimodal se houver; senão OCR local → texto para DeepSeek.
    """
    from integracoes.llm import LlmError, chat_completion_vision, obter_integracao_visao
    from integracoes.texto_local import extrair_texto_imagem_bytes, formatar_resultado_ocr

    file_field, nome, mime, ext = _resolver_anexo(ticket_id, attachment_ref)
    if not _eh_imagem(ext, mime or ''):
        raise AssistenteServiceError('O anexo não é uma imagem.')

    raw = _ler_bytes_anexo(file_field)
    if not raw:
        raise AssistenteServiceError('Arquivo de imagem vazio.')

    # Normaliza para JPEG (visão e OCR)
    raw_jpeg, mime_jpeg = _normalizar_imagem_para_visao(raw, mime or '', ext or '')
    if len(raw_jpeg) > 4 * 1024 * 1024:
        raise AssistenteServiceError(
            'Imagem ainda grande demais após compressão. Peça um print menor.'
        )

    metodo = 'ocr_local'
    descricao = ''
    integracao_visao = obter_integracao_visao()
    if integracao_visao:
        prompt = (
            'Descreva em português, de forma objetiva e útil para suporte de TI, o que aparece nesta imagem. '
            'Inclua textos visíveis (OCR), URLs, nomes de sistema (ex.: MoneyConsig, sistema.moneypromotora.com.br), '
            'números de telefone, nomes de campanha, erros na tela, menus/abas e qualquer detalhe relevante. '
            'Se reconhecer o sistema Money Promotora / MoneyConsig, diga explicitamente que é o sistema interno. '
            'Se a imagem estiver ilegível, diga isso claramente.'
        )
        try:
            descricao = chat_completion_vision(prompt, raw_jpeg, mime_jpeg or 'image/jpeg')
            metodo = f'visao:{integracao_visao.provider}'
        except LlmError as exc:
            logger.warning(
                'Visão falhou (%s); caindo para OCR local. Motivo: %s',
                integracao_visao.provider,
                exc,
            )

    if not descricao:
        try:
            texto = extrair_texto_imagem_bytes(raw_jpeg)
            descricao = formatar_resultado_ocr(texto, origem='imagem')
            metodo = 'ocr_local'
        except Exception as exc:
            logger.exception('OCR local falhou para anexo %s', attachment_ref)
            raise AssistenteServiceError(
                f'Não foi possível ler a imagem (OCR local): {exc}. '
                'Continue com título, descrição e categoria do chamado; '
                'não peça ao solicitante descrever o print se o texto já for suficiente.'
            ) from exc

    return {
        'ok': True,
        'ticket_id': ticket_id,
        'ref': attachment_ref,
        'nome': nome,
        'descricao': descricao,
        'metodo': metodo,
    }


def extrair_texto_pdf_anexo(ticket_id: int, attachment_ref: str) -> dict:
    """Extrai texto de PDF (nativo ou OCR local) para enviar ao LLM só-texto."""
    from integracoes.texto_local import extrair_texto_pdf_bytes, formatar_resultado_ocr

    file_field, nome, mime, ext = _resolver_anexo(ticket_id, attachment_ref)
    if not _eh_pdf(ext, mime or ''):
        raise AssistenteServiceError('O anexo não é um PDF.')

    raw = _ler_bytes_anexo(file_field)
    if not raw:
        raise AssistenteServiceError('Arquivo PDF vazio.')
    if len(raw) > 20 * 1024 * 1024:
        raise AssistenteServiceError('PDF maior que 20MB.')

    try:
        texto, metodo = extrair_texto_pdf_bytes(raw)
    except Exception as exc:
        logger.exception('Falha ao extrair PDF %s', attachment_ref)
        raise AssistenteServiceError(f'Falha ao ler PDF: {exc}') from exc

    origem = metodo if metodo in ('pdf_texto', 'pdf_ocr') else 'pdf_texto'
    return {
        'ok': True,
        'ticket_id': ticket_id,
        'ref': attachment_ref,
        'nome': nome,
        'descricao': formatar_resultado_ocr(texto, origem=origem),
        'metodo': metodo,
        'tem_texto': bool((texto or '').strip()),
    }


def ler_anexo_como_texto(ticket_id: int, attachment_ref: str) -> dict:
    """Imagem (visão/OCR) ou PDF → texto para o Assistente."""
    file_field, nome, mime, ext = _resolver_anexo(ticket_id, attachment_ref)
    if _eh_imagem(ext, mime or ''):
        return descrever_imagem_anexo(ticket_id, attachment_ref)
    if _eh_pdf(ext, mime or ''):
        return extrair_texto_pdf_anexo(ticket_id, attachment_ref)
    raise AssistenteServiceError(
        f'Anexo não suportado para leitura de texto ({ext or mime or nome}). '
        'Aceitos: imagem (jpg/png/webp/gif) ou PDF.'
    )


def consultar_chips(q: str, limit: int = 20) -> dict:
    """Busca chips por linha, observação ou nome do consultor (última entrega)."""
    from chips.models import Chip, ChipMovement

    termo = (q or '').strip()
    if not termo:
        raise AssistenteServiceError('Informe um termo de busca (nome do consultor ou número).')

    limit = max(1, min(int(limit or 20), 50))
    resultados: list[dict] = []
    visto: set[int] = set()

    # Chips cujo último movimento de entrega bate com o nome
    movs = (
        ChipMovement.objects.filter(
            action=ChipMovement.ActionChoices.DELIVERY,
            employee_name__icontains=termo,
        )
        .select_related('chip', 'chip__operator')
        .order_by('-timestamp')[:80]
    )
    for mov in movs:
        chip = mov.chip
        if chip.pk in visto:
            continue
        if chip.usage_status != Chip.UsageChoices.IN_USE:
            # ainda lista, mas marca
            pass
        visto.add(chip.pk)
        resultados.append({
            'id': chip.pk,
            'line_number': chip.line_number,
            'formatted_line_number': chip.formatted_line_number,
            'status': chip.status,
            'usage_status': chip.usage_status,
            'operator': chip.operator.name if chip.operator_id else None,
            'employee_name': mov.employee_name,
            'ultima_entrega': mov.timestamp.isoformat() if mov.timestamp else None,
            'match': 'entrega',
        })
        if len(resultados) >= limit:
            break

    if len(resultados) < limit:
        qs = (
            Chip.objects.filter(
                Q(line_number__icontains=termo)
                | Q(observacao__icontains=termo)
                | Q(iccid__icontains=termo)
            )
            .select_related('operator')
            .order_by('-updated_at')[:limit]
        )
        for chip in qs:
            if chip.pk in visto:
                continue
            visto.add(chip.pk)
            # Última entrega se houver
            last = (
                ChipMovement.objects.filter(
                    chip=chip, action=ChipMovement.ActionChoices.DELIVERY,
                )
                .order_by('-timestamp')
                .first()
            )
            resultados.append({
                'id': chip.pk,
                'line_number': chip.line_number,
                'formatted_line_number': chip.formatted_line_number,
                'status': chip.status,
                'usage_status': chip.usage_status,
                'operator': chip.operator.name if chip.operator_id else None,
                'employee_name': last.employee_name if last else None,
                'ultima_entrega': last.timestamp.isoformat() if last and last.timestamp else None,
                'match': 'linha_ou_obs',
            })
            if len(resultados) >= limit:
                break

    em_uso = [r for r in resultados if r.get('usage_status') == Chip.UsageChoices.IN_USE]
    return {
        'ok': True,
        'q': termo,
        'count': len(resultados),
        'em_uso_count': len(em_uso),
        'results': resultados,
        'orientacao': (
            'Se o consultor já tiver 2 números em uso, questionar se algum pede código '
            'antes de ativar chip novo.'
            if len(em_uso) >= 2
            else ''
        ),
    }


def consultar_usuario(q: str, limit: int = 15) -> dict:
    """Busca usuários CRM por username/nome/e-mail."""
    from core.models import CustomUser
    from mcp_api.serializers import filtro_q_usuario, serialize_user

    termo = (q or '').strip()
    if not termo:
        raise AssistenteServiceError('Informe username ou nome para buscar.')

    limit = max(1, min(int(limit or 15), 40))
    qs = filtro_q_usuario(
        CustomUser.objects.prefetch_related('equipes').order_by('username'),
        termo,
    ).distinct()[:limit]
    itens = []
    for u in qs:
        item = serialize_user(u)
        item['eh_membro_ti'] = usuario_eh_operador_helpdesk(u)
        itens.append(item)
    return {'ok': True, 'q': termo, 'count': len(itens), 'results': itens}


def atualizar_solicitante(
    ticket_id: int,
    user_id: int | None = None,
    nome_livre: str = '',
) -> dict:
    """
    Corrige o solicitante do chamado.
    - user_id: vincula usuário do sistema (tem acesso)
    - nome_livre: nome sem conta (sem requester_user)
    """
    from core.models import CustomUser
    from helpdesk.audit import log_edicao

    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    if not assistente_pode_atuar(ticket):
        raise AssistenteServiceError('Assistente não pode alterar este chamado agora.')

    antes_nome = ticket.requester_name
    antes_user_id = ticket.requester_user_id

    if user_id is not None and str(user_id).strip() != '':
        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            raise AssistenteServiceError('user_id inválido.')
        user = CustomUser.objects.filter(pk=uid, is_active=True).first()
        if not user:
            raise AssistenteServiceError('Usuário não encontrado ou inativo.', 404)
        if usuario_eh_operador_helpdesk(user):
            raise AssistenteServiceError(
                'Não defina membro da TI como solicitante. Peça o nome de quem sofreu o problema.'
            )
        ticket.requester_user = user
        ticket.requester_name = (user.get_full_name() or user.username)[:150]
        modo = 'usuario_sistema'
    else:
        nome = (nome_livre or '').strip()
        if not nome:
            raise AssistenteServiceError(
                'Informe user_id (usuário do sistema) ou nome_livre.'
            )
        ticket.requester_user = None
        ticket.requester_name = nome[:150]
        modo = 'nome_livre'

    ticket.save(update_fields=['requester_name', 'requester_user', 'updated_at'])
    Comment.objects.create(
        ticket=ticket,
        author=None,
        text=(
            f'Solicitante atualizado pelo Assistente de '
            f'"{antes_nome}" para "{ticket.requester_name}"'
            f'{" (usuário do sistema)" if ticket.requester_user_id else " (nome livre)"}.'
        ),
        is_assistente=True,
    )
    try:
        log_edicao(
            ticket,
            None,
            {
                'requester_name': {'antes': antes_nome, 'depois': ticket.requester_name},
                'requester_user_id': {'antes': antes_user_id, 'depois': ticket.requester_user_id},
            },
            f'Solicitante corrigido pelo Assistente para {ticket.requester_name}.',
        )
    except Exception:
        pass

    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'modo': modo,
        'requester_name': ticket.requester_name,
        'requester_user_id': ticket.requester_user_id,
        'antes': {'requester_name': antes_nome, 'requester_user_id': antes_user_id},
    }


def atualizar_descricao_chamado(
    ticket_id: int,
    description: str,
    title: str | None = None,
) -> dict:
    """Melhora título e/ou descrição do chamado (após confirmar o contexto)."""
    from helpdesk.audit import log_edicao

    ticket = Ticket.objects.filter(pk=ticket_id).first()
    if not ticket:
        raise AssistenteServiceError('Chamado não encontrado.', 404)
    if not assistente_pode_atuar(ticket):
        raise AssistenteServiceError('Assistente não pode alterar este chamado agora.')

    desc = (description or '').strip()
    if not desc:
        raise AssistenteServiceError('Informe a nova descrição.')
    if len(desc) > 8000:
        raise AssistenteServiceError('Descrição muito longa (máx. 8000 caracteres).')

    antes_desc = ticket.description
    antes_title = ticket.title
    campos = ['description', 'updated_at']
    ticket.description = desc

    titulo_novo = None
    if title is not None and str(title).strip():
        titulo_novo = str(title).strip()[:200]
        ticket.title = titulo_novo
        campos.append('title')

    ticket.save(update_fields=campos)
    Comment.objects.create(
        ticket=ticket,
        author=None,
        text='Descrição do chamado atualizada pelo Assistente para ficar mais clara.',
        is_assistente=True,
    )
    meta = {'description': {'antes': (antes_desc or '')[:200], 'depois': desc[:200]}}
    if titulo_novo is not None:
        meta['title'] = {'antes': antes_title, 'depois': titulo_novo}
    try:
        log_edicao(ticket, None, meta, 'Descrição/título atualizados pelo Assistente.')
    except Exception:
        pass

    return {
        'ok': True,
        'ticket_id': ticket.pk,
        'title': ticket.title,
        'description': ticket.description,
    }


# --- Discador (JoyTec) ---


def _resolver_discador(slug: str = 'joytec'):
    from discador.models import Discador
    from discador.services import get_or_create_joytec

    slug_limpo = (slug or 'joytec').strip().lower() or 'joytec'
    if slug_limpo == 'joytec':
        return get_or_create_joytec()
    discador = Discador.objects.filter(slug=slug_limpo, is_active=True).first()
    if not discador:
        raise AssistenteServiceError(f'Discador "{slug_limpo}" não encontrado.', 404)
    return discador


def _serialize_ramal(ramal) -> dict:
    acesso = None
    try:
        acesso = ramal.acesso
    except Exception:
        acesso = None
    return {
        'id': ramal.pk,
        'numero': ramal.numero,
        'status': ramal.status,
        'status_display': ramal.get_status_display(),
        'consome_licenca': ramal.consome_licenca,
        'tem_acesso': acesso is not None,
        'acesso_id': acesso.pk if acesso else None,
        'titular': (acesso.nome_exibicao if acesso else None),
        'login_discador': (acesso.login_discador if acesso else None),
    }


def _serialize_acesso(acesso) -> dict:
    return {
        'id': acesso.pk,
        'titular_nome': acesso.titular_nome,
        'titular': acesso.nome_exibicao,
        'titular_user_id': acesso.titular_user_id,
        'login_discador': acesso.login_discador,
        'tipo': acesso.tipo,
        'tipo_display': acesso.get_tipo_display(),
        'status': acesso.status,
        'ramal_id': acesso.ramal_id,
        'ramal': acesso.ramal.numero if acesso.ramal_id else None,
        'campanha_id': acesso.campanha_id,
        'campanha': acesso.campanha.nome if acesso.campanha_id else None,
    }


def consultar_licencas_discador(slug: str = 'joytec') -> dict:
    """KPIs de licenças: contratadas, livres (FREE), disponíveis no contrato, etc."""
    from discador.services import kpis_licencas

    discador = _resolver_discador(slug)
    kpis = kpis_licencas(discador)
    return {
        'ok': True,
        'discador': discador.nome,
        'slug': discador.slug,
        'contratadas': kpis['contratadas'],
        'consumidas': kpis['consumidas'],
        'em_uso': kpis['em_uso'],
        'ramais_livres': kpis['livres'],
        'nao_configurados': kpis['nao_configurados'],
        'licencas_disponiveis_contrato': kpis['disponiveis'],
        'estourado': kpis['estourado'],
        'no_limite': kpis['no_limite'],
        'custo_mensal': str(kpis['custo_mensal']),
        'orientacao': (
            'ramais_livres = status FREE (ainda consomem licença). '
            'licencas_disponiveis_contrato = slots novos no contrato. '
            'Para liberar slot do contrato, use liberar_licenca_ramal (NOT_CONFIGURED).'
        ),
    }


def listar_ramais_discador(
    status: str = '',
    slug: str = 'joytec',
    limit: int = 40,
) -> dict:
    """Lista ramais; status opcional: FREE|IN_USE|NOT_CONFIGURED."""
    from discador.models import Ramal

    discador = _resolver_discador(slug)
    limit = max(1, min(int(limit or 40), 80))
    qs = (
        Ramal.objects.filter(discador=discador)
        .select_related('acesso', 'acesso__campanha', 'acesso__titular_user')
        .order_by('numero')
    )
    status_limpo = (status or '').strip().upper()
    if status_limpo:
        validos = {c.value for c in Ramal.StatusChoices}
        if status_limpo not in validos:
            raise AssistenteServiceError(
                f'Status inválido. Use: {", ".join(sorted(validos))}.'
            )
        qs = qs.filter(status=status_limpo)

    itens = [_serialize_ramal(r) for r in qs[:limit]]
    return {
        'ok': True,
        'discador': discador.nome,
        'slug': discador.slug,
        'status': status_limpo or None,
        'count': len(itens),
        'results': itens,
    }


def consultar_acesso_discador(q: str, slug: str = 'joytec', limit: int = 20) -> dict:
    """Busca acessos por titular, login ou número do ramal."""
    from discador.models import AcessoDiscador

    termo = (q or '').strip()
    if not termo:
        raise AssistenteServiceError('Informe nome do titular, login ou ramal.')

    discador = _resolver_discador(slug)
    limit = max(1, min(int(limit or 20), 40))
    qs = (
        AcessoDiscador.objects.filter(discador=discador)
        .select_related('ramal', 'campanha', 'titular_user')
        .filter(
            Q(titular_nome__icontains=termo)
            | Q(login_discador__icontains=termo)
            | Q(ramal__numero__icontains=termo)
            | Q(titular_user__username__icontains=termo)
            | Q(titular_user__first_name__icontains=termo)
            | Q(titular_user__last_name__icontains=termo)
        )
        .order_by('titular_nome', 'login_discador')[:limit]
    )
    itens = [_serialize_acesso(a) for a in qs]
    return {
        'ok': True,
        'discador': discador.nome,
        'q': termo,
        'count': len(itens),
        'results': itens,
    }


def listar_campanhas_discador(slug: str = 'joytec', so_ativas: bool = True) -> dict:
    from discador.models import Campanha

    discador = _resolver_discador(slug)
    qs = Campanha.objects.filter(discador=discador).order_by('nome')
    if so_ativas:
        qs = qs.filter(is_active=True)
    itens = [
        {'id': c.pk, 'nome': c.nome, 'is_active': c.is_active}
        for c in qs[:80]
    ]
    return {
        'ok': True,
        'discador': discador.nome,
        'count': len(itens),
        'results': itens,
    }


def liberar_acesso_discador(acesso_id: int) -> dict:
    """Remove o acesso e deixa o ramal em FREE (ainda consome licença)."""
    from django.core.exceptions import ValidationError

    from discador.models import AcessoDiscador
    from discador.services import excluir_acesso

    acesso = (
        AcessoDiscador.objects.select_related('ramal', 'campanha')
        .filter(pk=acesso_id)
        .first()
    )
    if not acesso:
        raise AssistenteServiceError('Acesso não encontrado.', 404)
    ramal_numero = acesso.ramal.numero
    ramal_id = acesso.ramal_id
    titular = acesso.nome_exibicao
    try:
        excluir_acesso(acesso=acesso, actor=None)
    except ValidationError as exc:
        raise AssistenteServiceError(_msg_validacao(exc)) from exc
    return {
        'ok': True,
        'acesso_id': acesso_id,
        'titular': titular,
        'ramal_id': ramal_id,
        'ramal': ramal_numero,
        'status_ramal': 'FREE',
        'orientacao': (
            'Ramal liberado (FREE). Ainda consome licença. '
            'Para liberar slot do contrato use liberar_licenca_ramal.'
        ),
    }


def liberar_licenca_ramal(
    ramal_id: int | None = None,
    ramal_numero: str = '',
    slug: str = 'joytec',
) -> dict:
    """Marca ramal como NOT_CONFIGURED (deixa de consumir licença). Exige sem acesso."""
    from django.core.exceptions import ValidationError

    from discador.models import Ramal
    from discador.services import atualizar_ramal

    discador = _resolver_discador(slug)
    ramal = _buscar_ramal(discador, ramal_id=ramal_id, ramal_numero=ramal_numero)
    try:
        atualizar_ramal(
            ramal=ramal,
            numero=ramal.numero,
            status=Ramal.StatusChoices.NOT_CONFIGURED,
            actor=None,
        )
    except ValidationError as exc:
        raise AssistenteServiceError(_msg_validacao(exc)) from exc
    ramal.refresh_from_db()
    return {
        'ok': True,
        'ramal_id': ramal.pk,
        'ramal': ramal.numero,
        'status': ramal.status,
        'consome_licenca': ramal.consome_licenca,
    }


def criar_acesso_discador(
    titular_nome: str,
    login_discador: str,
    tipo: str = 'CONSULTOR',
    ramal_id: int | None = None,
    ramal_numero: str = '',
    campanha_id: int | None = None,
    campanha_nome: str = '',
    slug: str = 'joytec',
) -> dict:
    """Cria acesso em ramal FREE/NOT_CONFIGURED (escolhe FREE se ramal omitido)."""
    from django.core.exceptions import ValidationError

    from discador.models import AcessoDiscador, Campanha, Ramal
    from discador.services import criar_acesso, kpis_licencas

    discador = _resolver_discador(slug)
    titular = (titular_nome or '').strip()
    login = (login_discador or '').strip()
    if not login:
        raise AssistenteServiceError('login_discador é obrigatório.')

    tipo_limpo = (tipo or 'CONSULTOR').strip().upper()
    tipos = {c.value for c in AcessoDiscador.TipoChoices}
    if tipo_limpo not in tipos:
        raise AssistenteServiceError(f'Tipo inválido. Use: {", ".join(sorted(tipos))}.')

    campanha = _buscar_campanha(discador, campanha_id=campanha_id, campanha_nome=campanha_nome)
    if ramal_id or (ramal_numero or '').strip():
        ramal = _buscar_ramal(discador, ramal_id=ramal_id, ramal_numero=ramal_numero)
    else:
        ramal = (
            Ramal.objects.filter(discador=discador, status=Ramal.StatusChoices.FREE)
            .filter(acesso__isnull=True)
            .order_by('numero')
            .first()
        )
        if not ramal:
            # Tenta NOT_CONFIGURED se houver slot no contrato
            kpis = kpis_licencas(discador)
            if kpis['disponiveis'] <= 0:
                raise AssistenteServiceError(
                    'Sem ramais livres e sem licenças disponíveis no contrato. '
                    'Libere um acesso/licença ou peça aumento de contrato à TI.'
                )
            ramal = (
                Ramal.objects.filter(
                    discador=discador,
                    status=Ramal.StatusChoices.NOT_CONFIGURED,
                )
                .order_by('numero')
                .first()
            )
        if not ramal:
            raise AssistenteServiceError(
                'Não há ramal FREE/NOT_CONFIGURED disponível. Cadastre um ramal ou libere um.'
            )

    try:
        acesso = criar_acesso(
            discador=discador,
            titular_nome=titular,
            titular_user=None,
            login_discador=login,
            ramal=ramal,
            campanha=campanha,
            tipo=tipo_limpo,
            actor=None,
        )
    except ValidationError as exc:
        raise AssistenteServiceError(_msg_validacao(exc)) from exc

    return {
        'ok': True,
        'acesso': _serialize_acesso(acesso),
        'licencas': consultar_licencas_discador(slug),
    }


def _buscar_ramal(discador, *, ramal_id=None, ramal_numero: str = ''):
    from discador.models import Ramal

    if ramal_id:
        ramal = Ramal.objects.filter(pk=ramal_id, discador=discador).first()
        if not ramal:
            raise AssistenteServiceError('Ramal não encontrado.', 404)
        return ramal
    numero = (ramal_numero or '').strip()
    if not numero:
        raise AssistenteServiceError('Informe ramal_id ou ramal_numero.')
    ramal = Ramal.objects.filter(discador=discador, numero__iexact=numero).first()
    if not ramal:
        raise AssistenteServiceError(f'Ramal "{numero}" não encontrado.', 404)
    return ramal


def _buscar_campanha(discador, *, campanha_id=None, campanha_nome: str = ''):
    from discador.models import Campanha

    if campanha_id:
        campanha = Campanha.objects.filter(pk=campanha_id, discador=discador).first()
        if not campanha:
            raise AssistenteServiceError('Campanha não encontrada.', 404)
        return campanha
    nome = (campanha_nome or '').strip()
    if not nome:
        raise AssistenteServiceError('Informe campanha_id ou campanha_nome.')
    campanha = Campanha.objects.filter(
        discador=discador, nome__iexact=nome, is_active=True,
    ).first()
    if not campanha:
        campanha = Campanha.objects.filter(
            discador=discador, nome__icontains=nome, is_active=True,
        ).first()
    if not campanha:
        raise AssistenteServiceError(f'Campanha "{nome}" não encontrada.', 404)
    return campanha


def _msg_validacao(exc) -> str:
    if hasattr(exc, 'messages'):
        return '; '.join(str(m) for m in exc.messages)
    return str(exc)
