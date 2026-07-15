from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from core.audit import MODULO_CORE, logs_do_modulo, registrar_acao, registrar_alteracoes
from core.forms import CustomUserCreateForm, CustomUserUpdateForm, EquipeForm
from core.htmx import HtmxModalMixin
from core.models import CustomUser, Equipe, RegistroAcao
from core.permissions import MODULO_GESTAO_USUARIOS, ModuloObrigatorioMixin, requer_modulo


def erro_servidor(request):
    """Página amigável para erro 500 (produção com DEBUG=False)."""
    return render(request, '500.html', status=500)


def pagina_nao_encontrada(request, exception):
    """Página amigável para erro 404."""
    return render(request, '404.html', status=404)


def acesso_negado(request, exception):
    """Página amigável para erro 403."""
    return render(request, '403.html', status=403)


@login_required
def dashboard_view(request):
    """Tela inicial da aplicação (acessível a qualquer usuário autenticado)."""
    return render(request, 'core/dashboard.html')


@login_required
def sem_permissao_view(request):
    """Página exibida quando o usuário não tem acesso ao módulo solicitado."""
    return render(request, 'core/sem_permissao.html', status=403)


class UserListView(ModuloObrigatorioMixin, ListView):
    """Listagem de usuários do sistema (somente ADMIN)."""
    model = CustomUser
    template_name = 'core/user_list.html'
    context_object_name = 'usuarios'
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS

    def get_queryset(self):
        qs = CustomUser.objects.prefetch_related('equipes').order_by('-is_active', 'username')
        q = (self.request.GET.get('q') or '').strip()
        status = (self.request.GET.get('status') or '').strip().lower()

        if q:
            filtro = (
                Q(username__icontains=q)
                | Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
            )
            if q.isdigit():
                filtro |= Q(pk=int(q))
            qs = qs.filter(filtro)

        if status == 'ativo':
            qs = qs.filter(is_active=True)
        elif status == 'inativo':
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base = CustomUser.objects.all()
        context['total_usuarios'] = base.count()
        context['total_ativos'] = base.filter(is_active=True).count()
        context['total_inativos'] = base.filter(is_active=False).count()
        context['filtro_q'] = (self.request.GET.get('q') or '').strip()
        context['filtro_status'] = (self.request.GET.get('status') or '').strip().lower()
        context['audit_logs'] = logs_do_modulo(MODULO_CORE, limite=30)
        context['audit_titulo'] = 'Últimas ações de usuários e equipes'
        return context


class UserCreateView(HtmxModalMixin, ModuloObrigatorioMixin, CreateView):
    """Cadastro de novo usuário pelo ADMIN (modal HTMX na listagem)."""
    model = CustomUser
    form_class = CustomUserCreateForm
    list_url_name = 'user_list'
    modal_title = 'Novo Usuário'
    modal_subtitle = 'Cadastro realizado pelo administrador.'
    modal_submit_label = 'Salvar'
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS

    def form_valid(self, form):
        self.object = form.save()
        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.CREATED,
            descricao=f'Usuário "{self.object.username}" criado.',
            actor=self.request.user,
            obj=self.object,
            metadata={'role': self.object.role, 'is_active': self.object.is_active},
        )
        messages.success(self.request, f'Usuário "{form.instance.username}" criado com sucesso.')
        return self.htmx_redirect_response()


class UserUpdateView(HtmxModalMixin, ModuloObrigatorioMixin, UpdateView):
    """Edição de usuário existente (modal HTMX na listagem)."""
    model = CustomUser
    form_class = CustomUserUpdateForm
    list_url_name = 'user_list'
    modal_submit_label = 'Salvar'
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS
    context_object_name = 'usuario'

    def get_modal_title(self):
        return f'Editar Usuário — {self.object.username}'

    def get_modal_subtitle(self):
        return 'Atualize os dados de acesso e permissões.'

    def form_valid(self, form):
        antes = CustomUser.objects.get(pk=self.object.pk)
        self.object = form.save()
        registrar_alteracoes(
            modulo=MODULO_CORE,
            actor=self.request.user,
            obj_antes=antes,
            obj_depois=self.object,
            campos=['username', 'email', 'first_name', 'last_name', 'role', 'equipes', 'is_active', 'is_staff'],
            descricao_prefixo=f'Usuário "{self.object.username}" atualizado.',
        )
        messages.success(self.request, f'Usuário "{form.instance.username}" atualizado com sucesso.')
        return self.htmx_redirect_response()


@requer_modulo(MODULO_GESTAO_USUARIOS)
@require_POST
def user_toggle_active(request, pk):
    """Ativa ou desativa um usuário (soft delete via is_active)."""
    usuario = get_object_or_404(CustomUser, pk=pk)
    if usuario == request.user:
        messages.error(request, 'Você não pode desativar sua própria conta.')
        return redirect('user_list')

    usuario.is_active = not usuario.is_active
    usuario.save(update_fields=['is_active'])
    acao = 'ativado' if usuario.is_active else 'desativado'
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.ACTIVATED if usuario.is_active else RegistroAcao.AcaoChoices.DEACTIVATED,
        descricao=f'Usuário "{usuario.username}" {acao}.',
        actor=request.user,
        obj=usuario,
    )
    messages.success(request, f'Usuário "{usuario.username}" {acao} com sucesso.')
    return redirect('user_list')


@requer_modulo(MODULO_GESTAO_USUARIOS)
@require_POST
def user_delete(request, pk):
    """Remove permanentemente um usuário do sistema."""
    usuario = get_object_or_404(CustomUser, pk=pk)
    if usuario == request.user:
        messages.error(request, 'Você não pode excluir sua própria conta.')
        return redirect('user_list')

    username = usuario.username
    usuario.delete()
    
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.DELETED,
        descricao=f'Usuário "{username}" e todos os registros relacionados foram removidos permanentemente.',
        actor=request.user,
    )
    messages.success(request, f'Usuário "{username}" removido permanentemente com sucesso.')
    return redirect('user_list')


class EquipeListView(ModuloObrigatorioMixin, ListView):
    """Listagem de equipes do sistema (somente ADMIN)."""
    model = Equipe
    template_name = 'core/equipe_list.html'
    context_object_name = 'equipes'
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS

    def get_queryset(self):
        return Equipe.objects.all().order_by('-is_active', 'name')


class EquipeCreateView(HtmxModalMixin, ModuloObrigatorioMixin, CreateView):
    """Cadastro de nova equipe (modal HTMX na listagem)."""
    model = Equipe
    form_class = EquipeForm
    list_url_name = 'equipe_list'
    modal_title = 'Nova Equipe'
    modal_subtitle = 'Cadastro de equipe para agrupar usuários.'
    modal_submit_label = 'Salvar'
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS

    def form_valid(self, form):
        self.object = form.save()
        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.CREATED,
            descricao=f'Equipe "{self.object.name}" criada.',
            actor=self.request.user,
            obj=self.object,
        )
        messages.success(self.request, f'Equipe "{form.instance.name}" criada com sucesso.')
        return self.htmx_redirect_response()


class EquipeUpdateView(HtmxModalMixin, ModuloObrigatorioMixin, UpdateView):
    """Edição de equipe existente (modal HTMX na listagem)."""
    model = Equipe
    form_class = EquipeForm
    list_url_name = 'equipe_list'
    modal_submit_label = 'Salvar'
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS
    context_object_name = 'equipe'

    def get_modal_title(self):
        return f'Editar Equipe — {self.object.name}'

    def get_modal_subtitle(self):
        return 'Atualize os dados da equipe.'

    def form_valid(self, form):
        antes = Equipe.objects.get(pk=self.object.pk)
        self.object = form.save()
        registrar_alteracoes(
            modulo=MODULO_CORE,
            actor=self.request.user,
            obj_antes=antes,
            obj_depois=self.object,
            campos=['name', 'is_active'],
            descricao_prefixo=f'Equipe "{self.object.name}" atualizada.',
        )
        messages.success(self.request, f'Equipe "{form.instance.name}" atualizada com sucesso.')
        return self.htmx_redirect_response()


@requer_modulo(MODULO_GESTAO_USUARIOS)
@require_POST
def equipe_toggle_active(request, pk):
    """Ativa ou desativa uma equipe."""
    equipe = get_object_or_404(Equipe, pk=pk)
    equipe.is_active = not equipe.is_active
    equipe.save(update_fields=['is_active'])
    acao = 'ativada' if equipe.is_active else 'desativada'
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.ACTIVATED if equipe.is_active else RegistroAcao.AcaoChoices.DEACTIVATED,
        descricao=f'Equipe "{equipe.name}" {acao}.',
        actor=request.user,
        obj=equipe,
    )
    messages.success(request, f'Equipe "{equipe.name}" {acao} com sucesso.')
    return redirect('equipe_list')


class AuditoriaListView(ModuloObrigatorioMixin, ListView):
    """Página global de auditoria (somente ADMIN)."""
    model = RegistroAcao
    template_name = 'core/auditoria.html'
    context_object_name = 'registros'
    paginate_by = 20
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS

    def get_queryset(self):
        qs = RegistroAcao.objects.select_related('actor').order_by('-timestamp')
        params = self.request.GET

        modulo = params.get('modulo')
        acao = params.get('acao')
        actor = params.get('actor')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        search = params.get('search', '').strip()

        if modulo:
            qs = qs.filter(modulo=modulo)
        if acao:
            qs = qs.filter(acao=acao)
        if actor:
            qs = qs.filter(actor_id=actor)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        if search:
            qs = qs.filter(Q(descricao__icontains=search) | Q(object_repr__icontains=search))

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['modulo_choices'] = RegistroAcao.ModuloChoices.choices
        context['acao_choices'] = RegistroAcao.AcaoChoices.choices
        context['autores'] = CustomUser.objects.filter(acoes_registradas__isnull=False).distinct().order_by('username')
        context['filtros'] = {
            'modulo': self.request.GET.get('modulo', ''),
            'acao': self.request.GET.get('acao', ''),
            'actor': self.request.GET.get('actor', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'search': self.request.GET.get('search', ''),
        }
        return context
