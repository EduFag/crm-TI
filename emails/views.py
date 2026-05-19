from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, CreateView, View, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from emails.models import EmailAccount, EmailDomain

class DashboardView(LoginRequiredMixin, TemplateView):
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
        
        return context

class EmailAccountCreateView(LoginRequiredMixin, CreateView):
    """Cadastro de Novo E-mail (UX Melhorada com Dropdown de Domínio)"""
    model = EmailAccount
    fields = ['username', 'domain', 'employee_name', 'status']
    template_name = 'emails/account_form.html'
    success_url = reverse_lazy('emails:dashboard')
    
    def form_valid(self, form):
        messages.success(self.request, f"E-mail {form.instance.address} cadastrado com sucesso!")
        return super().form_valid(form)

class ResetPasswordView(LoginRequiredMixin, View):
    """Ação: Reset de Senha"""
    def post(self, request, pk):
        account = get_object_or_404(EmailAccount, pk=pk)
        account.last_password_reset = timezone.now()
        account.save()
        messages.success(request, f"Senha da conta {account.address} resetada. Uma notificação temporária foi gerada.")
        return redirect('emails:dashboard')

class ToggleAccountStatusView(LoginRequiredMixin, View):
    """Ação: Bloquear/Desbloquear Conta"""
    def post(self, request, pk):
        account = get_object_or_404(EmailAccount, pk=pk)
        if account.status == EmailAccount.StatusChoices.ACTIVE:
            account.status = EmailAccount.StatusChoices.BLOCKED
            action = "bloqueada"
        else:
            account.status = EmailAccount.StatusChoices.ACTIVE
            action = "desbloqueada"
        account.save()
        messages.success(request, f"A conta {account.address} foi {action} com sucesso.")
        return redirect('emails:dashboard')

# ===============================
# Gestão de Domínios
# ===============================
class EmailDomainListView(LoginRequiredMixin, ListView):
    model = EmailDomain
    template_name = 'emails/domain_list.html'
    context_object_name = 'domains'

class EmailDomainCreateView(LoginRequiredMixin, CreateView):
    model = EmailDomain
    fields = ['name']
    template_name = 'emails/form_base.html'
    success_url = reverse_lazy('emails:domain_list')
    
    def form_valid(self, form):
        # Limpar espaços ou '@' se o usuário digitar sem querer
        raw_name = form.instance.name.strip().lower()
        if raw_name.startswith('@'):
            raw_name = raw_name[1:]
        form.instance.name = raw_name
        
        messages.success(self.request, f"Domínio @{form.instance.name} adicionado ao catálogo!")
        return super().form_valid(form)
