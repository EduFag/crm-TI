from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.contrib import messages
from django.views.generic import View, TemplateView
from core.permissions import MODULO_CHIPS, ModuloObrigatorioMixin
from chips.models import Chip, ChipMovement


class _ChipsMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_CHIPS


class AssignmentView(_ChipsMixin, TemplateView):
    """Tela dupla: Formulário de Atribuição (Esquerda) e Estoque (Direita) - RF08, RF09, RF10"""
    template_name = 'chips/assignment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Exibe apenas os que têm status exato 'Disponível' (RF10)
        context['available_chips'] = Chip.objects.filter(status=Chip.StatusChoices.AVAILABLE).select_related('operator')
        return context
        
    def post(self, request, *args, **kwargs):
        chip_id = request.POST.get('chip_id')
        employee_name = request.POST.get('employee_name')
        
        chip = get_object_or_404(Chip, id=chip_id)
        
        # RF13 - Transferência Direta
        # Se o chip já estivesse em uso com alguém, geraríamos uma Devolução antes.
        if chip.status == Chip.StatusChoices.IN_USE:
            # Pega o último dono
            last_mov = chip.movements.filter(action=ChipMovement.ActionChoices.DELIVERY).order_by('-timestamp').first()
            old_emp = last_mov.employee_name if last_mov else "Desconhecido"
            
            ChipMovement.objects.create(
                chip=chip,
                employee_name=old_emp,
                action=ChipMovement.ActionChoices.RETURN,
                registered_by=request.user
            )
            messages.info(request, f"Posse anterior de {old_emp} encerrada automaticamente (Transferência).")
        
        # Registra Entrega
        ChipMovement.objects.create(
            chip=chip,
            employee_name=employee_name,
            action=ChipMovement.ActionChoices.DELIVERY,
            registered_by=request.user
        )
        
        # RF11 - Alterar status para Em Uso
        chip.status = Chip.StatusChoices.IN_USE
        chip.save()
        
        messages.success(request, f"Chip {chip.line_number} atribuído com sucesso para {employee_name}!")
        return redirect('chips:dashboard')

class ReturnChipView(_ChipsMixin, View):
    """Devolve um chip ao estoque (RF12)"""
    def post(self, request, pk):
        chip = get_object_or_404(Chip, pk=pk, status=Chip.StatusChoices.IN_USE)
        
        # Encontra com quem estava
        last_mov = chip.movements.filter(action=ChipMovement.ActionChoices.DELIVERY).order_by('-timestamp').first()
        old_emp = last_mov.employee_name if last_mov else "Desconhecido"
        
        ChipMovement.objects.create(
            chip=chip,
            employee_name=old_emp,
            action=ChipMovement.ActionChoices.RETURN,
            registered_by=request.user
        )
        
        chip.status = Chip.StatusChoices.AVAILABLE
        chip.save()
        
        messages.success(request, f"Chip {chip.line_number} retornado ao estoque.")
        return redirect('chips:dashboard')
