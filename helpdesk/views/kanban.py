import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView
from django.db.models import Case, When, IntegerField, Value
from core.models import CustomUser
from core.permissions import MODULO_HELPDESK, ModuloObrigatorioMixin, requer_modulo
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from helpdesk.forms import TicketCreateForm, TicketUpdateForm
from helpdesk.models import Ticket, TicketCategory, Comment
from helpdesk.audit import (
    log_atribuicao,
    log_chamado_criado,
    log_comentario,
    log_edicao,
    log_status_alterado,
    log_transferencia,
    log_chamado_excluido,
    log_chamado_recusado,
)
from helpdesk.ticket_access import (
    filtrar_chamados_para_usuario,
    usuario_pode_acessar_chamado,
    usuario_pode_editar_chamado,
    usuario_pode_gerenciar_categorias,
    usuario_pode_operar_kanban,
    usuario_pode_transferir_chamado,
    usuario_pode_ver_quem_abriu_chamado,
    usuarios_tecnicos_para_transferencia,
    usuario_pode_excluir_chamado,
)


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
        'pode_excluir': usuario_pode_excluir_chamado(request.user, ticket),
        'pode_transferir': usuario_pode_transferir_chamado(request.user),
        'tecnicos': usuarios_tecnicos_para_transferencia() if usuario_pode_transferir_chamado(request.user) else CustomUser.objects.none(),
        'edit_form': edit_form or (TicketUpdateForm(instance=ticket, user=request.user) if pode_editar else None),
        'mostrar_edicao': edit_form is not None,
    }

class KanbanView(ModuloObrigatorioMixin, TemplateView):
    template_name = 'helpdesk/kanban.html'
    modulo_obrigatorio = MODULO_HELPDESK

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Aplica a regra de arquivar antigos antes de carregar o kanban
        Ticket.archive_old_tickets(days_resolved=2, hours_rejected=24)
        
        # Apenas tickets ativos e NÃO arquivados no Kanban
        tickets = filtrar_chamados_para_usuario(
            Ticket.objects.filter(is_active=True, is_archived=False),
            self.request.user,
        ).select_related('assigned_to', 'created_by', 'requester_user', 'category')
        
        priority_ordering = Case(
            When(priority='URGENT', then=Value(4)),
            When(priority='HIGH', then=Value(3)),
            When(priority='MEDIUM', then=Value(2)),
            When(priority='LOW', then=Value(1)),
            default=Value(0),
            output_field=IntegerField()
        )
        
        tickets_annotated = tickets.annotate(priority_order=priority_ordering)
        
        context['tickets_new'] = tickets_annotated.filter(status=Ticket.StatusChoices.NEW).order_by('-priority_order', 'created_at')
        
        is_ti = self.request.user.role in ['ADMIN', 'IT_USER'] or self.request.user.is_superuser
        if is_ti:
            context['untriaged_count'] = sum(1 for t in context['tickets_new'] if not t.priority)
            
        context['tickets_in_progress'] = tickets_annotated.filter(status=Ticket.StatusChoices.IN_PROGRESS).order_by('-priority_order', '-created_at')
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
            status=422,
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
        }, status=422)

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
        
    ticket.unread_by_user = True
    ticket.unread_count_user += 1
    ticket.save()
    
    if status_anterior != Ticket.StatusChoices.RESOLVED:
        log_status_alterado(
            ticket,
            request.user,
            _rotulo_status(status_anterior),
            _rotulo_status(Ticket.StatusChoices.RESOLVED),
        )
        
    return JsonResponse({'success': True})


@requer_modulo(MODULO_HELPDESK)
def ticket_drawer(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related('assigned_to', 'created_by', 'requester_user', 'category'),
        pk=pk,
        is_active=True,
    )
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão para acessar este chamado.')
        
    is_ti = request.user.role in ['ADMIN', 'IT_USER'] or request.user.is_superuser
    changed = False
    if is_ti and (ticket.unread_by_tech or ticket.unread_count_tech > 0):
        ticket.unread_by_tech = False
        ticket.unread_count_tech = 0
        changed = True
    elif not is_ti and (ticket.unread_by_user or ticket.unread_count_user > 0):
        ticket.unread_by_user = False
        ticket.unread_count_user = 0
        changed = True
        
    if changed:
        ticket.save(update_fields=['unread_by_tech', 'unread_by_user', 'unread_count_tech', 'unread_count_user', 'updated_at'])
        response = render(request, 'helpdesk/_drawer.html', _contexto_drawer(request, ticket))
        response['HX-Trigger'] = json.dumps({'ticketUpdated': True})
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

    antes = Ticket.objects.select_related('assigned_to', 'category').get(pk=ticket.pk)
    form = TicketUpdateForm(request.POST, instance=ticket, user=request.user)
    if form.is_valid():
        depois = form.save()
        mensagens = gerar_comentarios_alteracao(antes, depois)
        for texto in mensagens:
            Comment.objects.create(ticket=depois, author=request.user, text=texto)
        metadata = _metadata_alteracao_ticket(antes, depois)
        if metadata:
            log_edicao(depois, request.user, metadata, '; '.join(mensagens))
            
        ticket.unread_by_user = True
        ticket.unread_count_user += 1
        ticket.save(update_fields=['unread_by_user', 'unread_count_user'])
        
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
        status=422,
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
    ticket.unread_by_user = True
    ticket.unread_count_user += 1
    ticket.save(update_fields=['unread_by_user', 'unread_count_user', 'updated_at'])
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
    if not usuario_pode_acessar_chamado(request.user, ticket):
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
        Comment.objects.create(ticket=ticket, author=request.user, text=text, attachment=attachment)
        if text:
            log_comentario(ticket, request.user, text)
        else:
            log_comentario(ticket, request.user, 'Anexou uma imagem.')
        
        is_ti = request.user.role in ['ADMIN', 'IT_USER'] or request.user.is_superuser
        if is_ti:
            ticket.unread_by_user = True
            ticket.unread_count_user += 1
        else:
            ticket.unread_by_tech = True
            ticket.unread_count_tech += 1
        ticket.save(update_fields=['unread_by_user', 'unread_by_tech', 'unread_count_user', 'unread_count_tech', 'updated_at'])
        
    comments = ticket.comments.filter(is_active=True).order_by('-created_at')
    response = render(request, 'helpdesk/_comments_list.html', {'ticket': ticket, 'comments': comments})
    response['HX-Trigger'] = json.dumps({'ticketUpdated': True})
    return response

@requer_modulo(MODULO_HELPDESK)
def ticket_comments(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk, is_active=True)
    if not usuario_pode_acessar_chamado(request.user, ticket):
        return HttpResponseForbidden('Sem permissão.')
        
    comments = ticket.comments.filter(is_active=True).order_by('-created_at')
    return render(request, 'helpdesk/_comments_list.html', {'ticket': ticket, 'comments': comments})

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
    if comment_id:
        from helpdesk.models import Comment
        comment = get_object_or_404(Comment, pk=comment_id, ticket=ticket)
        class MockAttachment:
            def __init__(self, file, created_at):
                self.file = file
                self.file_name = file.name.split('/')[-1] if file and file.name else 'anexo_comentario'
                self.created_at = created_at
        if comment.attachment:
            attachments = [MockAttachment(comment.attachment, comment.created_at)]
    else:
        attachments = ticket.attachments.all().order_by('-created_at')
    
    return render(request, 'helpdesk/_attachments_modal.html', {
        'ticket': ticket,
        'attachments': attachments
    })
