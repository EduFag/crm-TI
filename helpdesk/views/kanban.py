import json
import os
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView
from django.db.models import Case, When, IntegerField, Value
from core.models import CustomUser
from core.permissions import MODULO_HELPDESK, ModuloObrigatorioMixin, requer_modulo
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.db.models import Q
from helpdesk.forms import TicketCreateForm, TicketUpdateForm
from helpdesk.models import Ticket, TicketCategory, Comment, TicketContestation, TicketUnread
from helpdesk.audit import (
    log_atribuicao,
    log_chamado_criado,
    log_comentario,
    log_contestacao,
    log_edicao,
    log_prioridade_alterada,
    log_status_alterado,
    log_transferencia,
    log_chamado_excluido,
    log_chamado_recusado,
    log_triagem_alterada,
)
from helpdesk.mentions import marcar_mencoes_vistas, processar_mencoes
from helpdesk.notifications import (
    EVENTO_COMMENT,
    EVENTO_CREATED,
    EVENTO_PRIORITY_CHANGED,
    EVENTO_STATUS_CHANGED,
    EVENTO_TRIAGE_CHANGED,
    agendar_notificacao_chamado,
    agendar_notificacao_mencoes,
    destinatarios_finalizacao,
    destinatarios_notificacao,
)
from helpdesk.queue import aplicar_posicoes_fila
from helpdesk.ticket_access import (
    filtrar_chamados_para_usuario,
    usuario_eh_operador_helpdesk,
    usuario_pode_acessar_chamado,
    usuario_pode_comentar_chamado,
    usuario_pode_contestar_chamado,
    usuario_pode_editar_chamado,
    usuario_pode_gerenciar_categorias,
    usuario_pode_operar_kanban,
    usuario_pode_transferir_chamado,
    usuario_pode_ver_quem_abriu_chamado,
    usuarios_tecnicos_para_transferencia,
    usuario_pode_excluir_chamado,
)


def adicionar_nao_lido(ticket, ator, *, somente_nao_operadores=False, usuarios_extra=None):
    """Incrementa badge não-lido. usuarios_extra sempre recebe (ex.: @menções TI↔TI)."""
    from django.db.models import F
    if somente_nao_operadores:
        destinatarios = list(destinatarios_finalizacao(ticket, ator))
    else:
        destinatarios = list(destinatarios_notificacao(ticket, ator))

    ja_incluidos = {u.pk for u in destinatarios}
    for extra in usuarios_extra or []:
        if extra and extra.pk not in ja_incluidos and extra.is_active:
            destinatarios.append(extra)
            ja_incluidos.add(extra.pk)

    for usuario in destinatarios:
        obj, created = TicketUnread.objects.get_or_create(
            ticket=ticket, user=usuario,
            defaults={'count': 1}
        )
        if not created:
            obj.count = F('count') + 1
            obj.save(update_fields=['count'])


def _rotulo_prioridade(valor):
    if not valor:
        return 'Sem prioridade'
    return dict(Ticket.PriorityChoices.choices).get(valor, valor)


def _rotulo_status(valor):
    return dict(Ticket.StatusChoices.choices).get(valor, valor)


def _nome_usuario(user):
    if not user:
        return 'Não atribuído'
    return user.get_full_name() or user.username


def _autor_ultima_finalizacao(ticket):
    """Retorna autor do último comentário de finalização/recusa (fallback)."""
    comentario = (
        Comment.objects.filter(ticket=ticket, is_active=True)
        .filter(
            Q(text__startswith='Chamado finalizado') | Q(text__startswith='Chamado recusado')
        )
        .order_by('-created_at')
        .select_related('author')
        .first()
    )
    return comentario.author if comentario else None


def gerar_comentarios_alteracao(antes, depois):
    """Gera mensagens de histórico para campos alterados na edição."""
    mensagens = []
    if antes.title != depois.title:
        mensagens.append(f'Título alterado para "{depois.title}".')
    if (antes.description or '') != (depois.description or ''):
        mensagens.append('Descrição atualizada.')
    if antes.category_id != depois.category_id:
        mensagens.append(f'Categoria alterada para {depois.category.name}.')
    if antes.status != depois.status:
        mensagens.append(
            f'Status alterado de {_rotulo_status(antes.status)} para {_rotulo_status(depois.status)}.'
        )
    if antes.priority != depois.priority:
        mensagens.append(
            f'Prioridade alterada de {_rotulo_prioridade(antes.priority)} '
            f'para {_rotulo_prioridade(depois.priority)}.'
        )
    if antes.specific_category_id != depois.specific_category_id:
        antes_nome = antes.specific_category.name if antes.specific_category_id else 'Nenhuma'
        depois_nome = depois.specific_category.name if depois.specific_category_id else 'Nenhuma'
        mensagens.append(f'Triagem alterada de {antes_nome} para {depois_nome}.')
    if antes.requester_name != depois.requester_name or antes.requester_user_id != depois.requester_user_id:
        mensagens.append(f'Solicitante alterado para {depois.requester_name}.')
    if antes.assigned_to_id != depois.assigned_to_id:
        mensagens.append(
            f'Técnico transferido de {_nome_usuario(antes.assigned_to)} '
            f'para {_nome_usuario(depois.assigned_to)}.'
        )
    return mensagens


def _metadata_alteracao_ticket(antes, depois):
    """Monta metadata estruturada para edição de chamado."""
    metadata = {}
    if antes.title != depois.title:
        metadata['title'] = {'antes': antes.title, 'depois': depois.title}
    if antes.status != depois.status:
        metadata['status'] = {'antes': antes.status, 'depois': depois.status}
    if antes.priority != depois.priority:
        metadata['priority'] = {'antes': antes.priority, 'depois': depois.priority}
    if antes.specific_category_id != depois.specific_category_id:
        metadata['specific_category'] = {
            'antes': antes.specific_category_id,
            'depois': depois.specific_category_id,
        }
    if antes.category_id != depois.category_id:
        metadata['category'] = {'antes': str(antes.category), 'depois': str(depois.category)}
    if antes.requester_name != depois.requester_name:
        metadata['requester_name'] = {'antes': antes.requester_name, 'depois': depois.requester_name}
    if antes.assigned_to_id != depois.assigned_to_id:
        metadata['assigned_to'] = {
            'antes': _nome_usuario(antes.assigned_to),
            'depois': _nome_usuario(depois.assigned_to),
        }
    if (antes.description or '') != (depois.description or ''):
        metadata['description'] = {'antes': '...', 'depois': 'atualizada'}
    return metadata


def _contexto_drawer(request, ticket, edit_form=None):
    pode_editar = usuario_pode_editar_chamado(request.user, ticket)
    return {
        'ticket': ticket,
        'comments': ticket.comments.filter(is_active=True).order_by('-created_at'),
        'pode_ver_quem_abriu': usuario_pode_ver_quem_abriu_chamado(request.user, ticket),
        'pode_editar': pode_editar,
        'pode_comentar': usuario_pode_comentar_chamado(request.user, ticket),
        'pode_contestar': usuario_pode_contestar_chamado(request.user, ticket),
        'total_contestacoes': ticket.contestations.count(),
        'pode_excluir': usuario_pode_excluir_chamado(request.user, ticket),
        'pode_transferir': usuario_pode_transferir_chamado(request.user),
        'tecnicos': usuarios_tecnicos_para_transferencia() if usuario_pode_transferir_chamado(request.user) else CustomUser.objects.none(),
        'edit_form': edit_form or (TicketUpdateForm(instance=ticket, user=request.user) if pode_editar else None),
        'mostrar_edicao': edit_form is not None,
    }

class KanbanView(ModuloObrigatorioMixin, TemplateView):
    template_name = 'helpdesk/kanban.html'
    modulo_obrigatorio = MODULO_HELPDESK

    def dispatch(self, request, *args, **kwargs):
        # HTML/JS inline do helpdesk não fica preso em cache do browser
        response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Usa defaults do model — evita TypeError se deploy ficar com assinatura antiga
        Ticket.archive_old_tickets()
        
        # Apenas tickets ativos e NÃO arquivados no Kanban
        tickets = filtrar_chamados_para_usuario(
            Ticket.objects.filter(is_active=True, is_archived=False),
            self.request.user,
        ).select_related('assigned_to', 'created_by', 'requester_user', 'category', 'specific_category', 'equipe').prefetch_related('co_authors', 'attachments')
        
        priority_ordering = Case(
            When(priority='URGENT', then=Value(4)),
            When(priority='HIGH', then=Value(3)),
            When(priority='MEDIUM', then=Value(2)),
            When(priority='LOW', then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
        
        from django.db.models import Exists, OuterRef, Subquery
        from django.db.models.functions import Coalesce
        from helpdesk.models import TicketMention

        unread_subquery = TicketUnread.objects.filter(
            ticket_id=OuterRef('pk'),
            user=self.request.user
        ).values('count')[:1]
        unread_mention_exists = TicketMention.objects.filter(
            ticket_id=OuterRef('pk'),
            user=self.request.user,
            seen_at__isnull=True,
        )

        tickets_annotated = tickets.annotate(
            priority_order=priority_ordering,
            user_unread_count=Coalesce(Subquery(unread_subquery, output_field=IntegerField()), 0),
            has_unread_mention=Exists(unread_mention_exists),
        )

        tickets_new = list(
            tickets_annotated.filter(status=Ticket.StatusChoices.NEW).order_by('-priority_order', 'created_at')
        )
        tickets_in_progress = list(
            tickets_annotated.filter(status=Ticket.StatusChoices.IN_PROGRESS).order_by('-priority_order', '-created_at')
        )
        aplicar_posicoes_fila(tickets_new, tickets_in_progress)

        context['tickets_new'] = tickets_new

        is_ti = usuario_eh_operador_helpdesk(self.request.user)
        if is_ti:
            context['untriaged_count'] = sum(1 for t in tickets_new if not t.priority)
        else:
            context['untriaged_count'] = 0

        context['tickets_in_progress'] = tickets_in_progress
        context['tickets_pending'] = tickets_annotated.filter(status=Ticket.StatusChoices.PENDING).order_by('-priority_order', '-created_at')
        context['tickets_resolved'] = tickets_annotated.filter(status=Ticket.StatusChoices.RESOLVED).order_by('-updated_at')
        context['pode_operar_kanban'] = usuario_pode_operar_kanban(self.request.user)

        from helpdesk.models import TicketSpecificCategory
        context['specific_categories'] = TicketSpecificCategory.objects.filter(is_active=True).order_by('name')

        return context

class TicketCreateView(ModuloObrigatorioMixin, View):
    """Abre modal via HTMX (GET) e cria chamado via POST sem sair do Kanban."""
    modulo_obrigatorio = MODULO_HELPDESK
    template_name = 'helpdesk/_ticket_create_modal.html'

    def _nome_padrao(self, request):
        return request.user.get_full_name() or request.user.username

    def _contexto_modal(self, request, form, **extra):
        return {
            'form': form,
            'pode_gerenciar_categorias': usuario_pode_gerenciar_categorias(request.user),
            **extra,
        }

    def get(self, request):
        if not request.headers.get('HX-Request'):
            return redirect('helpdesk:kanban')
        form = TicketCreateForm(user=request.user, nome_solicitante_padrao=self._nome_padrao(request))
        return render(request, self.template_name, self._contexto_modal(request, form))

    def post(self, request):
        form = TicketCreateForm(
            request.POST,
            request.FILES,
            user=request.user,
            nome_solicitante_padrao=self._nome_padrao(request),
        )
        if form.is_valid():
            ticket = form.save(created_by=request.user)
            autor_nome = request.user.get_full_name() or request.user.username
            Comment.objects.create(
                ticket=ticket,
                author=request.user,
                text=f'Chamado aberto por {autor_nome}.',
            )
            log_chamado_criado(ticket, request.user)
            adicionar_nao_lido(ticket, request.user)
            agendar_notificacao_chamado(
                ticket,
                request.user,
                EVENTO_CREATED,
                f'Aberto por {_nome_usuario(request.user)}.',
            )
            response = HttpResponse(status=204)
            response['HX-Trigger'] = json.dumps({
                'ticketUpdated': True,
                'closeCreateModal': True,
            })
            return response
        return render(
            request,
            self.template_name,
            self._contexto_modal(request, form),
        )


@requer_modulo(MODULO_HELPDESK)
@require_POST
def ticket_category_create(request):
    """Cria categoria no modal (somente ADMIN/superuser) e atualiza o select via HTMX."""
    if not usuario_pode_gerenciar_categorias(request.user):
        return HttpResponseForbidden('Sem permissão para criar categorias.')

    nome = request.POST.get('name', '').strip()
    if not nome:
        form = TicketCreateForm(
            user=request.user,
            nome_solicitante_padrao=request.user.get_full_name() or request.user.username,
        )
        return render(request, 'helpdesk/_category_field.html', {
            'form': form,
            'pode_gerenciar_categorias': True,
            'erro_categoria': 'Informe o nome da categoria.',
            'painel_nova_categoria_aberto': True,
        })

    categoria = TicketCategory.objects.filter(name__iexact=nome).first()
    if categoria:
        if not categoria.is_active:
            categoria.is_active = True
            categoria.save(update_fields=['is_active'])
    else:
        categoria = TicketCategory.objects.create(name=nome)

    form = TicketCreateForm(
        user=request.user,
        nome_solicitante_padrao=request.user.get_full_name() or request.user.username,
        categoria_inicial=categoria.pk,
    )
    return render(request, 'helpdesk/_category_field.html', {
        'form': form,
        'pode_gerenciar_categorias': True,
    })


@requer_modulo(MODULO_HELPDESK)
@require_POST
def ticket_update_status(request, pk):
    if not usuario_pode_operar_kanban(request.user):
        return JsonResponse({'success': False, 'error': 'Sem permissão para mover chamados'}, status=403)

    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
    except json.JSONDecodeError:
        new_status = request.POST.get('status')

    if new_status in dict(Ticket.StatusChoices.choices):
        status_anterior = ticket.status
        prioridade_anterior = ticket.priority
        triagem_anterior = ticket.specific_category

        ticket.status = new_status

        priority = data.get('priority')
        if priority is not None:
            ticket.priority = priority or None

        specific_category_id = data.get('specific_category')
        if specific_category_id is not None:
            ticket.specific_category_id = specific_category_id if specific_category_id else None

        if not ticket.assigned_to and new_status != Ticket.StatusChoices.NEW:
            ticket.assigned_to = request.user
            Comment.objects.create(
                ticket=ticket,
                author=request.user,
                text=f'Chamado atribuído automaticamente a {request.user.username} (movimentado para {ticket.get_status_display()}).'
            )
            log_atribuicao(
                ticket,
                request.user,
                descricao_extra=f'(movimentado para {ticket.get_status_display()})',
            )
        ticket.save()
        if status_anterior != new_status:
            log_status_alterado(
                ticket,
                request.user,
                _rotulo_status(status_anterior),
                _rotulo_status(new_status),
            )
            agendar_notificacao_chamado(
                ticket,
                request.user,
                EVENTO_STATUS_CHANGED,
                f'Movido para {_rotulo_status(new_status)}.',
            )
        if prioridade_anterior != ticket.priority:
            log_prioridade_alterada(ticket, request.user, prioridade_anterior, ticket.priority)
            agendar_notificacao_chamado(
                ticket,
                request.user,
                EVENTO_PRIORITY_CHANGED,
                f'Prioridade: {_rotulo_prioridade(prioridade_anterior)} → {_rotulo_prioridade(ticket.priority)}.',
            )
        triagem_depois = ticket.specific_category
        if triagem_anterior != triagem_depois:
            log_triagem_alterada(ticket, request.user, triagem_anterior, triagem_depois)
            depois_nome = triagem_depois.name if triagem_depois else 'Nenhuma'
            agendar_notificacao_chamado(
                ticket,
                request.user,
                EVENTO_TRIAGE_CHANGED,
                f'Triagem: {depois_nome}.',
            )
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Status inválido'}, status=400)


@requer_modulo(MODULO_HELPDESK)
@require_POST
def ticket_finalize(request, pk):
    if not usuario_pode_operar_kanban(request.user):
        return JsonResponse({'success': False, 'error': 'Sem permissão para mover chamados'}, status=403)

    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return JsonResponse({'success': False, 'error': 'Sem permissão'}, status=403)
        
    try:
        data = json.loads(request.body)
        action = data.get('action')
        reason = data.get('reason')
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Payload inválido'}, status=400)
        
    if not reason:
        return JsonResponse({'success': False, 'error': 'Observação / Motivo é obrigatório'}, status=400)
        
    status_anterior = ticket.status
    ticket.status = Ticket.StatusChoices.RESOLVED
    
    if action == 'reject':
        ticket.is_rejected = True
        ticket.rejection_reason = reason
        log_chamado_recusado(ticket, request.user, reason)
        Comment.objects.create(
            ticket=ticket, 
            author=request.user, 
            text=f"Chamado recusado.\nMotivo: {reason}"
        )
    else:
        ticket.is_rejected = False
        # Remove a recusa anterior caso seja re-resolvido
        ticket.rejection_reason = ""
        Comment.objects.create(
            ticket=ticket, 
            author=request.user, 
            text=f"Chamado finalizado.\nObservação: {reason}"
        )
        
    if not ticket.assigned_to:
        ticket.assigned_to = request.user

    ticket.resolved_by = request.user
    ticket.save()
    # Finalizados: badge/push só para não-operadores (solicitante, criador, etc.)
    adicionar_nao_lido(ticket, request.user, somente_nao_operadores=True)

    if status_anterior != Ticket.StatusChoices.RESOLVED:
        log_status_alterado(
            ticket,
            request.user,
            _rotulo_status(status_anterior),
            _rotulo_status(Ticket.StatusChoices.RESOLVED),
        )
        agendar_notificacao_chamado(
            ticket,
            request.user,
            EVENTO_STATUS_CHANGED,
            f'Movido para {_rotulo_status(Ticket.StatusChoices.RESOLVED)}.',
            somente_nao_operadores=True,
        )

    return JsonResponse({'success': True})


@requer_modulo(MODULO_HELPDESK)
@require_POST
def ticket_contest(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_contestar_chamado(request.user, ticket):
        return JsonResponse({'success': False, 'error': 'Sem permissão para contestar este chamado'}, status=403)

    try:
        data = json.loads(request.body)
        reason = (data.get('reason') or '').strip()
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Payload inválido'}, status=400)

    if not reason:
        return JsonResponse({'success': False, 'error': 'Motivo da contestação é obrigatório'}, status=400)

    finalized_by = ticket.resolved_by or _autor_ultima_finalizacao(ticket)
    finalized_at = ticket.resolved_at
    was_rejected = ticket.is_rejected
    finalized_by_nome = _nome_usuario(finalized_by)

    TicketContestation.objects.create(
        ticket=ticket,
        contested_by=request.user,
        reason=reason,
        finalized_by=finalized_by,
        finalized_at=finalized_at,
        was_rejected=was_rejected,
    )

    rotulo_finalizacao = 'recusado' if was_rejected else 'finalizado'
    data_fmt = finalized_at.strftime('%d/%m/%Y %H:%M') if finalized_at else 'data não registrada'
    Comment.objects.create(
        ticket=ticket,
        author=request.user,
        text=(
            f'Contestação do chamado.\n'
            f'Motivo: {reason}\n'
            f'(Havia sido {rotulo_finalizacao} por {finalized_by_nome} em {data_fmt})'
        ),
    )

    status_anterior = ticket.status
    ticket.status = Ticket.StatusChoices.NEW
    ticket.is_rejected = False
    ticket.rejection_reason = ''
    ticket.save()
    adicionar_nao_lido(ticket, request.user)

    log_status_alterado(
        ticket,
        request.user,
        _rotulo_status(status_anterior),
        _rotulo_status(Ticket.StatusChoices.NEW),
    )
    log_contestacao(ticket, request.user, reason, finalized_by_nome)
    agendar_notificacao_chamado(
        ticket,
        request.user,
        EVENTO_STATUS_CHANGED,
        f'Contestado — voltou para {_rotulo_status(Ticket.StatusChoices.NEW)}.',
    )

    response = JsonResponse({'success': True})
    response['HX-Trigger'] = json.dumps({'ticketUpdated': True})
    return response


@requer_modulo(MODULO_HELPDESK)
def ticket_drawer(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related('assigned_to', 'created_by', 'requester_user', 'category').prefetch_related('co_authors'),
        pk=pk,
        is_active=True,
    )
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão para acessar este chamado.')
        
    deleted, _ = TicketUnread.objects.filter(ticket=ticket, user=request.user).delete()
    mencoes_vistas = marcar_mencoes_vistas(ticket, request.user)
    if deleted or mencoes_vistas:
        response = render(request, 'helpdesk/_drawer.html', _contexto_drawer(request, ticket))
        response['HX-Trigger'] = json.dumps({'ticketUpdated': True, 'ticketRead': True})
        return response

    return render(request, 'helpdesk/_drawer.html', _contexto_drawer(request, ticket))


@requer_modulo(MODULO_HELPDESK)
def ticket_edit(request, pk):
    """Exibe ou salva edição de chamado."""
    ticket = get_object_or_404(
        Ticket.objects.select_related('assigned_to', 'created_by', 'requester_user', 'category'),
        pk=pk,
        is_active=True,
    )
    if not usuario_pode_editar_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão para editar chamados.')

    if request.method == 'GET':
        return render(
            request,
            'helpdesk/_drawer.html',
            _contexto_drawer(request, ticket, edit_form=TicketUpdateForm(instance=ticket, user=request.user)),
        )

    antes = Ticket.objects.select_related('assigned_to', 'category', 'specific_category').get(pk=ticket.pk)
    form = TicketUpdateForm(request.POST, instance=ticket, user=request.user)
    if form.is_valid():
        depois = form.save()
        mensagens = gerar_comentarios_alteracao(antes, depois)
        for texto in mensagens:
            Comment.objects.create(ticket=depois, author=request.user, text=texto)
        metadata = _metadata_alteracao_ticket(antes, depois)
        if metadata:
            log_edicao(depois, request.user, metadata, '; '.join(mensagens))

        if 'status' in metadata:
            msg_status = next((m for m in mensagens if m.startswith('Status')), None)
            agendar_notificacao_chamado(
                depois,
                request.user,
                EVENTO_STATUS_CHANGED,
                msg_status or f'Movido para {_rotulo_status(depois.status)}.',
            )
        if 'priority' in metadata:
            msg_prioridade = next((m for m in mensagens if m.startswith('Prioridade')), 'Prioridade alterada.')
            agendar_notificacao_chamado(
                depois,
                request.user,
                EVENTO_PRIORITY_CHANGED,
                msg_prioridade,
            )
        if 'specific_category' in metadata:
            msg_triagem = next((m for m in mensagens if m.startswith('Triagem')), 'Triagem alterada.')
            agendar_notificacao_chamado(
                depois,
                request.user,
                EVENTO_TRIAGE_CHANGED,
                msg_triagem,
            )

        ticket.save()
        adicionar_nao_lido(ticket, request.user)
        
        ticket.refresh_from_db()
        response = render(
            request,
            'helpdesk/_drawer.html',
            _contexto_drawer(request, ticket),
        )
        response['HX-Trigger'] = json.dumps({'ticketUpdated': True})
        return response

    return render(
        request,
        'helpdesk/_drawer.html',
        _contexto_drawer(request, ticket, edit_form=form),
    )


@requer_modulo(MODULO_HELPDESK)
@require_POST
def ticket_transfer(request, pk):
    """Transferência rápida de técnico responsável (somente ADMIN/superuser)."""
    if not usuario_pode_transferir_chamado(request.user):
        return HttpResponseForbidden('Sem permissão para transferir chamados.')

    ticket = get_object_or_404(
        Ticket.objects.select_related('assigned_to'),
        pk=pk,
        is_active=True,
    )
    tecnico_id = request.POST.get('assigned_to')
    if not tecnico_id:
        return HttpResponseForbidden('Selecione um técnico.')

    tecnico = get_object_or_404(usuarios_tecnicos_para_transferencia(), pk=tecnico_id)
    if ticket.assigned_to_id == tecnico.pk:
        return render(request, 'helpdesk/_drawer.html', _contexto_drawer(request, ticket))

    anterior = ticket.assigned_to
    ticket.assigned_to = tecnico
    ticket.save(update_fields=['assigned_to', 'updated_at'])
    Comment.objects.create(
        ticket=ticket,
        author=request.user,
        text=(
            f'Técnico transferido de {_nome_usuario(anterior)} '
            f'para {_nome_usuario(tecnico)}.'
        ),
    )
    log_transferencia(
        ticket,
        request.user,
        _nome_usuario(anterior),
        _nome_usuario(tecnico),
    )
    ticket.save(update_fields=['updated_at'])
    adicionar_nao_lido(ticket, request.user)
    ticket.refresh_from_db()
    response = render(
        request,
        'helpdesk/_drawer.html',
        _contexto_drawer(request, ticket),
    )
    response['HX-Trigger'] = json.dumps({'ticketUpdated': True})
    return response


@requer_modulo(MODULO_HELPDESK)
@require_POST
def ticket_add_comment(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_comentar_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão para comentar neste chamado.')
    text = request.POST.get('text', '').strip()
    attachment = request.FILES.get('attachment')
    if text or attachment:
        if attachment:
            from django.core.exceptions import ValidationError
            from helpdesk.models import validate_image_attachment
            try:
                validate_image_attachment(attachment)
            except ValidationError as e:
                return HttpResponse(e.messages[0], status=400)
        comment = Comment.objects.create(
            ticket=ticket, author=request.user, text=text, attachment=attachment,
        )
        # Menções @: só operadores; concede co_authors + notifica (inclui TI↔TI)
        mencionados = processar_mencoes(ticket, comment, request.user) if text else []

        if text:
            meta = {}
            if mencionados:
                meta['mention_user_ids'] = [u.pk for u in mencionados]
                meta['acao_ui'] = 'MENTION'
            log_comentario(ticket, request.user, text, metadata=meta or None)
        else:
            log_comentario(ticket, request.user, 'Anexou uma imagem.')

        ticket.save(update_fields=['updated_at'])
        # Badge geral + mencionados (silêncio TI não se aplica a quem foi @mencionado)
        adicionar_nao_lido(ticket, request.user, usuarios_extra=mencionados)

        preview = text[:120] if text else 'Nova imagem anexada.'
        agendar_notificacao_chamado(ticket, request.user, EVENTO_COMMENT, preview)
        if mencionados:
            # Push dedicado de menção — ignora silêncio TI↔TI
            agendar_notificacao_mencoes(ticket, mencionados, preview)

    comments = ticket.comments.filter(is_active=True).order_by('-created_at')
    response = render(request, 'helpdesk/_comments_list.html', {'ticket': ticket, 'comments': comments})
    response['HX-Trigger'] = json.dumps({'ticketUpdated': True})
    return response


@requer_modulo(MODULO_HELPDESK)
def mention_users_search(request):
    """Autocomplete de @username — exclusivo para operadores helpdesk."""
    if not usuario_eh_operador_helpdesk(request.user):
        return JsonResponse({'results': []}, status=403)

    q = (request.GET.get('q') or '').strip().lstrip('@')
    qs = CustomUser.objects.filter(is_active=True).exclude(pk=request.user.pk)
    if q:
        qs = qs.filter(
            Q(username__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
        )
    qs = qs.order_by('username')[:15]
    results = [
        {
            'username': u.username,
            'label': u.get_full_name() or u.username,
        }
        for u in qs
    ]
    return JsonResponse({'results': results})

@requer_modulo(MODULO_HELPDESK)
def ticket_comments(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão.')

    deleted, _ = TicketUnread.objects.filter(ticket=ticket, user=request.user).delete()
    mencoes_vistas = marcar_mencoes_vistas(ticket, request.user)
    comments = ticket.comments.filter(is_active=True).order_by('-created_at')

    response = render(request, 'helpdesk/_comments_list.html', {'ticket': ticket, 'comments': comments})
    if deleted or mencoes_vistas:
        response['HX-Trigger'] = json.dumps({'ticketRead': True})
    return response

class KanbanBoardPartialView(KanbanView):
    """Retorna apenas o HTML do quadro para ser injetado via HTMX no evento SSE."""
    template_name = 'helpdesk/_kanban_board.html'


@requer_modulo(MODULO_HELPDESK)
@require_POST
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_excluir_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão para excluir chamados.')
    ticket.is_active = False
    ticket.save()
    log_chamado_excluido(ticket, request.user)
    
    if request.headers.get('HX-Request'):
        response = HttpResponse("")
        response['HX-Trigger'] = json.dumps({'ticketUpdated': True})
        return response
        
    return redirect('helpdesk:kanban')


@requer_modulo(MODULO_HELPDESK)
def ticket_attachments(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão para visualizar este chamado.')
        
    attachments = []
    comment_id = request.GET.get('comment_id')

    class MockAttachment:
        def __init__(self, file, created_at):
            self.file = file
            self.file_name = file.name.split('/')[-1] if file and file.name else 'anexo_comentario'
            self.created_at = created_at
        
        @property
        def is_image(self):
            ext = os.path.splitext(self.file.name)[1].lower() if self.file and self.file.name else ''
            return ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']

        @property
        def is_audio(self):
            ext = os.path.splitext(self.file.name)[1].lower() if self.file and self.file.name else ''
            return ext in ['.mp3', '.wav', '.ogg', '.m4a']

        @property
        def extension(self):
            ext = os.path.splitext(self.file.name)[1].lower() if self.file and self.file.name else ''
            return ext[1:] if ext else ''

    if comment_id:
        from helpdesk.models import Comment
        comment = get_object_or_404(Comment, pk=comment_id, ticket=ticket)
        if comment.attachment:
            attachments = [MockAttachment(comment.attachment, comment.created_at)]
    else:
        tipo = request.GET.get('type')
        qs = ticket.attachments.all().order_by('-created_at')
        if tipo == 'images':
            attachments = [att for att in qs if att.is_image]
        elif tipo == 'audios':
            attachments = [att for att in qs if att.is_audio]
        elif tipo == 'docs':
            attachments = [att for att in qs if not att.is_image and not att.is_audio]
        else:
            attachments = list(qs)
            
    has_images = any(a.is_image for a in attachments)
    
    return render(request, 'helpdesk/_attachments_modal.html', {
        'ticket': ticket,
        'attachments': attachments,
        'has_images': has_images,
    })
