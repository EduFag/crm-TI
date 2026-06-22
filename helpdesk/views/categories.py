from django.views.generic import TemplateView
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from core.permissions import MODULO_HELPDESK, ModuloObrigatorioMixin, requer_modulo, resposta_sem_permissao
from helpdesk.models import TicketCategory, TicketSpecificCategory
from helpdesk.ticket_access import usuario_pode_gerenciar_categorias

class CategoriesManageView(ModuloObrigatorioMixin, TemplateView):
    template_name = 'helpdesk/_categories_modal.html'
    modulo_obrigatorio = MODULO_HELPDESK
    
    def dispatch(self, request, *args, **kwargs):
        if not usuario_pode_gerenciar_categorias(request.user):
            return resposta_sem_permissao(request)
        return super().dispatch(request, *args, **kwargs)
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['general_categories'] = TicketCategory.objects.all().order_by('name')
        context['specific_categories'] = TicketSpecificCategory.objects.all().order_by('name')
        return context

@requer_modulo(MODULO_HELPDESK)
@require_POST
def category_toggle_active(request, model_type, pk):
    if not usuario_pode_gerenciar_categorias(request.user):
        return HttpResponseForbidden('Acesso negado.')
        
    model = TicketCategory if model_type == 'general' else TicketSpecificCategory
    category = get_object_or_404(model, pk=pk)
    
    category.is_active = not category.is_active
    category.save(update_fields=['is_active'])
    
    return render(request, 'helpdesk/_category_row.html', {
        'category': category,
        'type': model_type
    })

@requer_modulo(MODULO_HELPDESK)
@require_POST
def category_create_action(request, model_type):
    if not usuario_pode_gerenciar_categorias(request.user):
        return HttpResponseForbidden('Acesso negado.')
        
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Nome é obrigatório.'})
        
    model = TicketCategory if model_type == 'general' else TicketSpecificCategory
    
    category, created = model.objects.get_or_create(
        name__iexact=name,
        defaults={'name': name, 'is_active': True}
    )
    if not created and not category.is_active:
        category.is_active = True
        category.save(update_fields=['is_active'])
        
    if request.headers.get('HX-Request'):
        categories = model.objects.all().order_by('name')
        return render(request, 'helpdesk/_category_list.html', {
            'categories': categories,
            'type': model_type
        })
        
    return JsonResponse({'success': True})

@requer_modulo(MODULO_HELPDESK)
@require_POST
def category_delete(request, model_type, pk):
    if not usuario_pode_gerenciar_categorias(request.user):
        return HttpResponseForbidden('Acesso negado.')
        
    model = TicketCategory if model_type == 'general' else TicketSpecificCategory
    category = get_object_or_404(model, pk=pk)
    
    # Store name for audit
    name = category.name
    category.delete()
    
    # Render nothing (or a 200 OK) to let HTMX remove the row
    return HttpResponse(status=200)
