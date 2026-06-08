from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from core.forms import CustomUserCreateForm, CustomUserUpdateForm, EquipeForm
from core.models import CustomUser, Equipe
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
        return CustomUser.objects.select_related('equipe').order_by('-is_active', 'username')


class UserCreateView(ModuloObrigatorioMixin, CreateView):
    """Cadastro de novo usuário pelo ADMIN (sem auto-registro público)."""
    model = CustomUser
    form_class = CustomUserCreateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('user_list')
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS

    def form_valid(self, form):
        messages.success(self.request, f'Usuário "{form.instance.username}" criado com sucesso.')
        return super().form_valid(form)


class UserUpdateView(ModuloObrigatorioMixin, UpdateView):
    """Edição de usuário existente."""
    model = CustomUser
    form_class = CustomUserUpdateForm
    template_name = 'core/user_form.html'
    success_url = reverse_lazy('user_list')
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS
    context_object_name = 'usuario'

    def form_valid(self, form):
        messages.success(self.request, f'Usuário "{form.instance.username}" atualizado com sucesso.')
        return super().form_valid(form)


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
    messages.success(request, f'Usuário "{usuario.username}" {acao} com sucesso.')
    return redirect('user_list')


class EquipeListView(ModuloObrigatorioMixin, ListView):
    """Listagem de equipes do sistema (somente ADMIN)."""
    model = Equipe
    template_name = 'core/equipe_list.html'
    context_object_name = 'equipes'
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS

    def get_queryset(self):
        return Equipe.objects.all().order_by('-is_active', 'name')


class EquipeCreateView(ModuloObrigatorioMixin, CreateView):
    """Cadastro de nova equipe."""
    model = Equipe
    form_class = EquipeForm
    template_name = 'core/equipe_form.html'
    success_url = reverse_lazy('equipe_list')
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS

    def form_valid(self, form):
        messages.success(self.request, f'Equipe "{form.instance.name}" criada com sucesso.')
        return super().form_valid(form)


class EquipeUpdateView(ModuloObrigatorioMixin, UpdateView):
    """Edição de equipe existente."""
    model = Equipe
    form_class = EquipeForm
    template_name = 'core/equipe_form.html'
    success_url = reverse_lazy('equipe_list')
    modulo_obrigatorio = MODULO_GESTAO_USUARIOS
    context_object_name = 'equipe'

    def form_valid(self, form):
        messages.success(self.request, f'Equipe "{form.instance.name}" atualizada com sucesso.')
        return super().form_valid(form)


@requer_modulo(MODULO_GESTAO_USUARIOS)
@require_POST
def equipe_toggle_active(request, pk):
    """Ativa ou desativa uma equipe."""
    equipe = get_object_or_404(Equipe, pk=pk)
    equipe.is_active = not equipe.is_active
    equipe.save(update_fields=['is_active'])
    acao = 'ativada' if equipe.is_active else 'desativada'
    messages.success(request, f'Equipe "{equipe.name}" {acao} com sucesso.')
    return redirect('equipe_list')
