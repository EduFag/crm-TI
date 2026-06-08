from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView, UpdateView
from django.contrib import messages

from core.permissions import MODULO_EQUIPMENT, ModuloObrigatorioMixin
from .models import Equipment, EquipmentLog


class _EquipmentMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_EQUIPMENT


class DashboardView(_EquipmentMixin, TemplateView):
    """ RF01: Dashboard com Métricas Consolidadas """
    template_name = 'equipment/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        # RF01: Indicadores Consolidados
        context['total_equipments'] = Equipment.objects.count()
        context['available_equipments'] = Equipment.objects.filter(status=Equipment.StatusChoices.AVAILABLE).count()
        context['in_use_equipments'] = Equipment.objects.filter(status=Equipment.StatusChoices.IN_USE).count()
        context['maintenance_equipments'] = Equipment.objects.filter(status=Equipment.StatusChoices.MAINTENANCE).count()
        context['expired_warranty'] = Equipment.objects.filter(warranty_end__lt=today).count()
        
        # Listas para as Tabelas
        context['equipments'] = Equipment.objects.all().order_by('-created_at')
        context['history_logs'] = EquipmentLog.objects.all().select_related('equipment')[:50]
        
        return context

class EquipmentCreateView(_EquipmentMixin, CreateView):
    """ RF04: Cadastro de Novo Ativo """
    model = Equipment
    template_name = 'equipment/form.html'
    fields = ['type', 'tag', 'serial_number', 'brand_model', 'purchase_date', 'warranty_end', 'purchase_value', 'status', 'current_employee']
    success_url = reverse_lazy('equipment:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        
        # RF02: Log de Criação Automática
        action = EquipmentLog.ActionChoices.CREATED
        if form.instance.status == Equipment.StatusChoices.IN_USE:
            action = EquipmentLog.ActionChoices.ASSIGNED
            
        EquipmentLog.objects.create(
            equipment=form.instance,
            action=action,
            employee_name=form.instance.current_employee or "Sistema"
        )
        
        messages.success(self.request, f"Equipamento {form.instance.tag} cadastrado com sucesso!")
        return response

class EquipmentUpdateView(_EquipmentMixin, UpdateView):
    """ Edição e Mudança de Status do Ativo """
    model = Equipment
    template_name = 'equipment/form.html'
    fields = ['type', 'tag', 'serial_number', 'brand_model', 'purchase_date', 'warranty_end', 'purchase_value', 'status', 'current_employee']
    success_url = reverse_lazy('equipment:dashboard')

    def form_valid(self, form):
        old_equipment = Equipment.objects.get(pk=self.object.pk)
        old_status = old_equipment.status
        old_employee = old_equipment.current_employee
        
        response = super().form_valid(form)
        
        # RF02: Histórico de Atribuições Inteligente
        if old_status != form.instance.status or old_employee != form.instance.current_employee:
            action = EquipmentLog.ActionChoices.ASSIGNED

            if form.instance.status == Equipment.StatusChoices.IN_USE:
                action = EquipmentLog.ActionChoices.ASSIGNED
            elif old_status == Equipment.StatusChoices.IN_USE and form.instance.status == Equipment.StatusChoices.AVAILABLE:
                action = EquipmentLog.ActionChoices.RETURNED
            elif form.instance.status == Equipment.StatusChoices.MAINTENANCE:
                action = EquipmentLog.ActionChoices.MAINTENANCE
            elif form.instance.status == Equipment.StatusChoices.SCRAP:
                action = EquipmentLog.ActionChoices.SCRAPPED
                
            EquipmentLog.objects.create(
                equipment=form.instance,
                action=action,
                employee_name=form.instance.current_employee or old_employee or "Sistema"
            )
            
        messages.success(self.request, f"Equipamento {form.instance.tag} atualizado!")
        return response
