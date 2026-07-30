from django import forms
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, FormView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Count, Q

from core.htmx import HtmxModalMixin
from core.permissions import ModuloObrigatorioMixin, MODULO_OPERADORES
from core.models import Equipe
from .models import Operador, WhatsAppAccount, PA, Ilha
from .forms import OperadorForm, WhatsAppAccountForm, PAForm, IlhaForm, PABatchForm, AlocarOperadorForm

class DashboardView(ModuloObrigatorioMixin, ListView):
    modulo_obrigatorio = MODULO_OPERADORES
    model = PA
    template_name = 'operadores/dashboard.html'
    context_object_name = 'pas'

    def get_queryset(self):
        qs = PA.objects.select_related('ilha', 'ilha__setor', 'operador').prefetch_related(
            'operador__whatsapp_accounts', 
            'operador__whatsapp_accounts__chip'
        ).all()
        
        q = (self.request.GET.get('q') or '').strip()
        setor_id = self.request.GET.get('setor')
        ilha_id = self.request.GET.get('ilha')

        if setor_id:
            qs = qs.filter(ilha__setor_id=setor_id)
        if ilha_id:
            qs = qs.filter(ilha_id=ilha_id)

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(ilha__name__icontains=q) |
                Q(ilha__setor__name__icontains=q) |
                Q(operador__name__icontains=q) |
                Q(operador__whatsapp_accounts__phone_number__icontains=q)
            ).distinct()

        return qs.order_by('ilha__setor__name', 'ilha__name', 'name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_tab = self.request.GET.get('tab', 'overview')
        q = (self.request.GET.get('q') or '').strip()
        setor_id = self.request.GET.get('setor', '')
        ilha_id = self.request.GET.get('ilha', '')

        operadores_qs = Operador.objects.select_related('pa', 'pa__ilha', 'pa__ilha__setor').prefetch_related('whatsapp_accounts', 'whatsapp_accounts__chip').all()
        if q:
            operadores_qs = operadores_qs.filter(
                Q(name__icontains=q) |
                Q(pa__name__icontains=q) |
                Q(pa__ilha__name__icontains=q) |
                Q(whatsapp_accounts__phone_number__icontains=q)
            ).distinct()

        total_pas = PA.objects.count()
        pas_ocupadas = PA.objects.filter(operador__isnull=False).count()
        pas_livres = total_pas - pas_ocupadas
        total_operadores = Operador.objects.count()
        
        whatsapp_accounts = WhatsAppAccount.objects.select_related(
            'operador', 
            'chip', 
            'operador__pa', 
            'operador__pa__ilha', 
            'operador__pa__ilha__setor'
        ).all()
        
        if q:
            whatsapp_accounts = whatsapp_accounts.filter(
                Q(phone_number__icontains=q) |
                Q(chip__line_number__icontains=q) |
                Q(operador__name__icontains=q) |
                Q(operador__pa__name__icontains=q)
            ).distinct()

        whatsapp_status = self.request.GET.get('status', '')
        if whatsapp_status:
            whatsapp_accounts = whatsapp_accounts.filter(status=whatsapp_status)

        total_whatsapp_accounts = WhatsAppAccount.objects.count()
        whatsapp_ativas = WhatsAppAccount.objects.filter(status=WhatsAppAccount.StatusChoices.ACTIVE).count()
        whatsapp_banidas = WhatsAppAccount.objects.filter(status=WhatsAppAccount.StatusChoices.BANNED).count()

        # Setores e Ilhas para os filtros
        setores_list = Equipe.objects.filter(is_active=True).order_by('name')
        ilhas_qs = Ilha.objects.select_related('setor').all()
        if setor_id:
            ilhas_qs = ilhas_qs.filter(setor_id=setor_id)
        ilhas_list = ilhas_qs.order_by('name')

        context.update({
            'active_tab': active_tab,
            'operadores': operadores_qs,
            'whatsapp_accounts_list': whatsapp_accounts,
            'whatsapp_status': whatsapp_status,
            'total_whatsapp_accounts': total_whatsapp_accounts,
            'total_operadores': total_operadores,
            'total_pas': total_pas,
            'pas_ocupadas': pas_ocupadas,
            'pas_livres': pas_livres,
            'whatsapp_ativas': whatsapp_ativas,
            'whatsapp_banidas': whatsapp_banidas,
            'setores_list': setores_list,
            'ilhas_list': ilhas_list,
            'selected_setor': setor_id,
            'selected_ilha': ilha_id,
            'q': q,
        })
        return context

class PABatchCreateView(HtmxModalMixin, ModuloObrigatorioMixin, FormView):
    modulo_obrigatorio = MODULO_OPERADORES
    form_class = PABatchForm
    modal_title = 'Gerenciar / Criar PAs em Lote'
    modal_subtitle = 'Crie múltiplas ilhas e PAs para um setor/equipe de forma automática.'
    modal_submit_label = 'Gerar PAs'
    list_url_name = 'operadores:dashboard'

    def form_valid(self, form):
        equipe = form.cleaned_data['equipe']
        num_ilhas = form.cleaned_data['num_ilhas']
        pas_per_ilha = form.cleaned_data['pas_per_ilha']
        ilha_prefix = form.cleaned_data['ilha_prefix'].strip()
        pa_prefix = form.cleaned_data['pa_prefix'].strip()

        created_pas_count = 0
        created_ilhas_count = 0

        for i in range(1, num_ilhas + 1):
            ilha_name = f"{ilha_prefix} {i:02d}" if num_ilhas > 1 else ilha_prefix
            ilha, created_ilha = Ilha.objects.get_or_create(
                name=ilha_name,
                setor=equipe
            )
            if created_ilha:
                created_ilhas_count += 1

            for j in range(1, pas_per_ilha + 1):
                pa_name = f"{pa_prefix} {j:02d}"
                _, created_pa = PA.objects.get_or_create(
                    name=pa_name,
                    ilha=ilha
                )
                if created_pa:
                    created_pas_count += 1

        messages.success(
            self.request,
            f"Lote processado! Criadas {created_ilhas_count} novas ilha(s) e {created_pas_count} nova(s) PA(s) no setor {equipe.name}."
        )
        return self.htmx_redirect_response()

class OperadorCreateView(HtmxModalMixin, ModuloObrigatorioMixin, CreateView):
    modulo_obrigatorio = MODULO_OPERADORES
    model = Operador
    form_class = OperadorForm
    modal_title = 'Novo Funcionário / Operador'
    modal_submit_label = 'Cadastrar Funcionário'
    list_url_name = 'operadores:dashboard'

    def get_initial(self):
        initial = super().get_initial()
        pa_id = self.request.GET.get('pa_id')
        if pa_id:
            initial['pa'] = pa_id
        return initial

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Funcionário cadastrado com sucesso!")
        return self.htmx_redirect_response(url=reverse('operadores:dashboard') + '?tab=funcionarios')

class OperadorUpdateView(HtmxModalMixin, ModuloObrigatorioMixin, UpdateView):
    modulo_obrigatorio = MODULO_OPERADORES
    model = Operador
    form_class = OperadorForm
    modal_title = 'Editar Funcionário / Operador'
    modal_submit_label = 'Salvar Alterações'
    list_url_name = 'operadores:dashboard'

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Funcionário atualizado com sucesso!")
        return self.htmx_redirect_response(url=reverse('operadores:dashboard') + '?tab=funcionarios')

class OperadorDeleteView(ModuloObrigatorioMixin, View):
    modulo_obrigatorio = MODULO_OPERADORES

    def post(self, request, pk):
        operador = get_object_or_404(Operador, pk=pk)
        nome = operador.name
        operador.delete()
        messages.success(request, f"Funcionário '{nome}' removido com sucesso!")
        return redirect(reverse('operadores:dashboard') + '?tab=funcionarios')

class WhatsAppAccountCreateView(HtmxModalMixin, ModuloObrigatorioMixin, CreateView):
    modulo_obrigatorio = MODULO_OPERADORES
    model = WhatsAppAccount
    form_class = WhatsAppAccountForm
    modal_title = 'Nova Conta WhatsApp'
    modal_submit_label = 'Cadastrar Conta'
    list_url_name = 'operadores:dashboard'

    def get_initial(self):
        initial = super().get_initial()
        operador_id = self.request.GET.get('operador_id')
        if operador_id:
            initial['operador'] = operador_id
        return initial

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if form.initial.get('operador'):
             form.fields['operador'].widget = forms.HiddenInput()
        return form

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Conta WhatsApp cadastrada e linha atualizada!")
        return self.htmx_redirect_response(url=reverse('operadores:dashboard') + '?tab=funcionarios')

class WhatsAppAccountUpdateView(HtmxModalMixin, ModuloObrigatorioMixin, UpdateView):
    modulo_obrigatorio = MODULO_OPERADORES
    model = WhatsAppAccount
    form_class = WhatsAppAccountForm
    modal_title = 'Editar Conta WhatsApp'
    modal_submit_label = 'Salvar Alterações'
    list_url_name = 'operadores:dashboard'

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "Conta WhatsApp atualizada!")
        return self.htmx_redirect_response(url=reverse('operadores:dashboard') + '?tab=funcionarios')

class PACreateView(HtmxModalMixin, ModuloObrigatorioMixin, CreateView):
    modulo_obrigatorio = MODULO_OPERADORES
    model = PA
    form_class = PAForm
    modal_title = 'Nova PA (Posição de Atendimento)'
    modal_submit_label = 'Cadastrar PA'
    list_url_name = 'operadores:dashboard'

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "PA cadastrada com sucesso!")
        return self.htmx_redirect_response()

class PAUpdateView(HtmxModalMixin, ModuloObrigatorioMixin, UpdateView):
    modulo_obrigatorio = MODULO_OPERADORES
    model = PA
    form_class = PAForm
    modal_title = 'Editar PA'
    modal_submit_label = 'Salvar'
    list_url_name = 'operadores:dashboard'

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, "PA atualizada com sucesso!")
        return self.htmx_redirect_response()

class IlhaUpdateView(HtmxModalMixin, ModuloObrigatorioMixin, UpdateView):
    modulo_obrigatorio = MODULO_OPERADORES
    model = Ilha
    form_class = IlhaForm
    modal_title = 'Editar Ilha'
    modal_submit_label = 'Salvar Alterações'
    list_url_name = 'operadores:dashboard'

    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, f"Ilha '{self.object.name}' atualizada com sucesso!")
        return self.htmx_redirect_response()

class PADeleteView(ModuloObrigatorioMixin, View):
    modulo_obrigatorio = MODULO_OPERADORES

    def post(self, request, pk):
        pa = get_object_or_404(PA, pk=pk)
        nome = pa.name
        pa.delete()
        messages.success(request, f"PA '{nome}' removida com sucesso!")
        return redirect('operadores:dashboard')

class AlocarOperadorView(HtmxModalMixin, ModuloObrigatorioMixin, FormView):
    modulo_obrigatorio = MODULO_OPERADORES
    form_class = AlocarOperadorForm
    modal_submit_label = 'Alocar Operador'
    list_url_name = 'operadores:dashboard'

    def dispatch(self, request, *args, **kwargs):
        self.pa = get_object_or_404(PA.objects.select_related('ilha', 'ilha__setor'), pk=self.kwargs['pa_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_modal_title(self):
        return f"Alocar Operador — {self.pa.ilha.setor.name} - {self.pa.ilha.name} - {self.pa.name}"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['pa'] = self.pa
        return kwargs

    def form_valid(self, form):
        operador = form.cleaned_data['operador']

        # Desaloca o operador anterior que estava nesta PA, se houver
        if hasattr(self.pa, 'operador') and self.pa.operador and self.pa.operador != operador:
            old_op = self.pa.operador
            old_op.pa = None
            old_op.save(update_fields=['pa'])

        operador.pa = self.pa
        operador.save(update_fields=['pa'])

        messages.success(
            self.request,
            f"Operador '{operador.name}' alocado com sucesso em {self.pa.ilha.setor.name} - {self.pa.name}!"
        )
        return self.htmx_redirect_response()

class OperadorWhatsAppManageView(ModuloObrigatorioMixin, View):
    modulo_obrigatorio = MODULO_OPERADORES

    def get(self, request, operador_id):
        operador = get_object_or_404(Operador, pk=operador_id)
        accounts = operador.whatsapp_accounts.select_related('chip').all()
        return render(request, 'operadores/modals/operador_whatsapp_manage.html', {
            'operador': operador,
            'accounts': accounts,
        })

class OperadorProfileModalView(ModuloObrigatorioMixin, View):
    modulo_obrigatorio = MODULO_OPERADORES

    def get(self, request, pk):
        operador = get_object_or_404(Operador, pk=pk)
        return render(request, 'operadores/modals/operador_profile.html', {
            'operador': operador,
        })

class WhatsAppAccountChangeStatusView(ModuloObrigatorioMixin, View):
    modulo_obrigatorio = MODULO_OPERADORES

    def post(self, request, pk):
        account = get_object_or_404(WhatsAppAccount, pk=pk)
        new_status = request.POST.get('status')
        if new_status in WhatsAppAccount.StatusChoices.values:
            account.status = new_status
            account.save(update_fields=['status'])
            messages.success(
                request,
                f"Status da conta WhatsApp alterado para '{account.get_status_display()}' com sucesso!"
            )

        if request.headers.get('HX-Request'):
            from django.http import HttpResponse
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('operadores:dashboard') + '?tab=funcionarios'
            return response

        return redirect(reverse('operadores:dashboard') + '?tab=funcionarios')
