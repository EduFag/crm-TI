from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView, UpdateView

from core.forms import CustomUserCreateForm, CustomUserUpdateForm
from core.models import CustomUser
from core.permissions import MODULO_GESTAO_USUARIOS, ModuloObrigatorioMixin, requer_modulo


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
        return CustomUser.objects.all().order_by('-is_active', 'username')


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
