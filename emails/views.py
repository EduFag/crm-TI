from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import TemplateView, CreateView, View, ListView
from django.contrib import messages

from core.permissions import MODULO_EMAILS, ModuloObrigatorioMixin
from core.audit import logs_do_modulo
from core.htmx import HtmxModalMixin
from emails.models import EmailAccount, EmailDomain
from emails.audit import (
    log_conta_bloqueada,
    log_conta_criada,
    log_conta_desbloqueada,
    log_dominio_criado,
    log_reset_senha,
)


class _EmailsMixin(ModuloObrigatorioMixin):
    modulo_obrigatorio = MODULO_EMAILS


class DashboardView(_EmailsMixin, TemplateView):
    """Página Unificada: Métricas + Inventário + Filtros"""
    template_name = 'emails/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Métricas
        context['active_accounts'] = EmailAccount.objects.filter(status=EmailAccount.StatusChoices.ACTIVE).count()
        context['blocked_accounts'] = EmailAccount.objects.filter(status=EmailAccount.StatusChoices.BLOCKED).count()
        
        # Inventário e Filtros
        context['accounts'] = EmailAccount.objects.select_related('domain').all().order_by('employee_name')
        context['domains'] = EmailDomain.objects.all().order_by('name')
        context['audit_logs'] = logs_do_modulo(MODULO_EMAILS, limite=50)
        context['audit_titulo'] = 'Registro de auditoria de e-mails'
        
        return context

class EmailAccountCreateView(HtmxModalMixin, _EmailsMixin, CreateView):
    """Cadastro de novo e-mail via modal no dashboard."""
    model = EmailAccount
    fields = ['username', 'domain', 'employee_name', 'password', 'status']
    modal_template_name = 'emails/_account_form_modal.html'
    list_url_name = 'emails:dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_action'] = reverse('emails:account_create')
        context['modal_title'] = 'Novo E-mail'
        context['modal_subtitle'] = 'Crie a identidade e o acesso da caixa corporativa.'
        context['modal_submit_label'] = 'Criar Conta'
        return context
    
    def form_valid(self, form):
        self.object = form.save()
        log_conta_criada(self.object, self.request.user)
        messages.success(self.request, f"E-mail {form.instance.address} cadastrado com sucesso!")
        return self.htmx_redirect_response()

from django.urls import reverse, reverse_lazy
from django.views.generic import UpdateView, DeleteView

class EmailAccountUpdateView(HtmxModalMixin, _EmailsMixin, UpdateView):
    """Edição de e-mail."""
    model = EmailAccount
    fields = ['username', 'domain', 'employee_name', 'password', 'status']
    modal_template_name = 'emails/_account_form_modal.html'
    list_url_name = 'emails:dashboard'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_action'] = reverse('emails:account_update', args=[self.object.pk])
        context['modal_title'] = 'Editar E-mail'
        context['modal_subtitle'] = f'Atualize os dados da caixa {self.object.address}.'
        context['modal_submit_label'] = 'Salvar Alterações'
        return context

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"E-mail {form.instance.address} atualizado com sucesso!")
        return self.htmx_redirect_response()

class EmailAccountDeleteView(_EmailsMixin, DeleteView):
    """Exclusão de e-mail via POST direto."""
    model = EmailAccount
    success_url = reverse_lazy('emails:dashboard')
    
    def form_valid(self, form):
        address = self.object.address
        messages.success(self.request, f"E-mail {address} excluído permanentemente.")
        return super().form_valid(form)

from django.http import HttpResponse

class EmailAccountViewPasswordModal(HtmxModalMixin, _EmailsMixin, View):
    """Visualização da senha protegida por verificação de segurança."""
    
    def get(self, request, pk):
        account = get_object_or_404(EmailAccount, pk=pk)
        return render(request, 'emails/_view_password_modal.html', {'account': account, 'password_visible': False})
        
    def post(self, request, pk):
        account = get_object_or_404(EmailAccount, pk=pk)
        admin_password = request.POST.get('admin_password', '')
        
        if request.user.check_password(admin_password):
            return render(request, 'emails/_view_password_modal.html', {'account': account, 'password_visible': True, 'account_password': account.password})
        else:
            return render(request, 'emails/_view_password_modal.html', {'account': account, 'password_visible': False, 'error': 'Senha incorreta. Acesso negado.'})




class ToggleAccountStatusView(_EmailsMixin, View):
    """Ação: Bloquear/Desbloquear Conta"""
    def post(self, request, pk):
        account = get_object_or_404(EmailAccount, pk=pk)
        if account.status == EmailAccount.StatusChoices.ACTIVE:
            account.status = EmailAccount.StatusChoices.BLOCKED
            action = "bloqueada"
            log_conta_bloqueada(account, request.user)
        else:
            account.status = EmailAccount.StatusChoices.ACTIVE
            action = "desbloqueada"
            log_conta_desbloqueada(account, request.user)
        account.save()
        messages.success(request, f"A conta {account.address} foi {action} com sucesso.")
        return redirect('emails:dashboard')

# ===============================
# Gestão de Domínios
# ===============================
class EmailDomainCreateView(HtmxModalMixin, _EmailsMixin, CreateView):
    model = EmailDomain
    fields = ['name']
    list_url_name = 'emails:dashboard'
    modal_title = 'Novo Domínio'
    modal_subtitle = 'Adicione um domínio corporativo autorizado (ex: empresa.com.br).'
    modal_submit_label = 'Salvar'
    form_layout = 'as_p'
    
    def form_valid(self, form):
        # Limpar espaços ou '@' se o usuário digitar sem querer
        raw_name = form.instance.name.strip().lower()
        if raw_name.startswith('@'):
            raw_name = raw_name[1:]
        form.instance.name = raw_name
        self.object = form.save()
        log_dominio_criado(self.object, self.request.user)
        messages.success(self.request, f"Domínio @{form.instance.name} adicionado ao catálogo!")
        return self.htmx_redirect_response()

    def htmx_redirect_response(self, url_name=None):
        from django.urls import reverse
        from django.http import HttpResponse
        url = reverse('emails:dashboard') + '?tab=domains'
        response = HttpResponse(status=204)
        response['HX-Redirect'] = url
        return response
