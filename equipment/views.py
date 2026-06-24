from django.utils import timezone
from django.views.generic import TemplateView, CreateView, UpdateView
from django.contrib import messages

from core.audit import logs_do_modulo
from core.permissions import MODULO_EQUIPMENT, ModuloObrigatorioMixin
from core.htmx import HtmxModalMixin
from equipment.audit import log_cadastro, log_edicao_cadastral, log_do_equipment_log
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
        context['audit_logs'] = logs_do_modulo(MODULO_EQUIPMENT, limite=50)
        context['audit_titulo'] = 'Registro de auditoria de equipamentos'
        
        return context

class EquipmentCreateView(HtmxModalMixin, _EquipmentMixin, CreateView):
    """ RF04: Cadastro de novo ativo via modal no dashboard """
    model = Equipment
    list_url_name = 'equipment:dashboard'
    modal_title = 'Novo Ativo de TI'
    modal_subtitle = 'Insira patrimônio, série, garantia e demais dados.'
    modal_submit_label = 'Gravar Patrimônio'
    modal_max_width = 'max-w-2xl'
    form_layout = 'as_p'
    fields = ['type', 'tag', 'serial_number', 'brand_model', 'purchase_date', 'warranty_end', 'purchase_value', 'status', 'current_employee']

    def form_valid(self, form):
        self.object = form.save()
        
        # RF02: Log de Criação Automática
        action = EquipmentLog.ActionChoices.CREATED
        if form.instance.status == Equipment.StatusChoices.IN_USE:
            action = EquipmentLog.ActionChoices.ASSIGNED
            
        EquipmentLog.objects.create(
            equipment=form.instance,
            action=action,
            employee_name=form.instance.current_employee or "Sistema"
        )
        log_cadastro(
            form.instance,
            action,
            form.instance.current_employee or "Sistema",
            self.request.user,
        )
        
        messages.success(self.request, f"Equipamento {form.instance.tag} cadastrado com sucesso!")
        return self.htmx_redirect_response()

class EquipmentUpdateView(HtmxModalMixin, _EquipmentMixin, UpdateView):
    """ Edição e mudança de status do ativo via modal """
    model = Equipment
    list_url_name = 'equipment:dashboard'
    modal_submit_label = 'Salvar Alterações'
    modal_max_width = 'max-w-2xl'
    form_layout = 'as_p'
    fields = ['type', 'tag', 'serial_number', 'brand_model', 'purchase_date', 'warranty_end', 'purchase_value', 'status', 'current_employee']

    def get_modal_title(self):
        return f'Editar Ativo — {self.object.tag}'

    def get_modal_subtitle(self):
        return 'Atualize dados e status do patrimônio.'

    def form_valid(self, form):
        old_equipment = Equipment.objects.get(pk=self.object.pk)
        old_status = old_equipment.status
        old_employee = old_equipment.current_employee
        
        self.object = form.save()
        
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
            log_do_equipment_log(
                form.instance,
                action,
                form.instance.current_employee or old_employee or "Sistema",
                self.request.user,
            )

        log_edicao_cadastral(form.instance, self.request.user, old_equipment)
            
        messages.success(self.request, f"Equipamento {form.instance.tag} atualizado!")
        return self.htmx_redirect_response()
