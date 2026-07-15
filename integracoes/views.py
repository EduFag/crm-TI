"""Views da listagem e wizard de integrações IA."""

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import ListView

from core.audit import MODULO_CORE, registrar_acao
from core.models import RegistroAcao
from core.permissions import MODULO_INTEGRACOES, ModuloObrigatorioMixin, requer_modulo
from integracoes.models import IntegracaoIA
from integracoes.providers import (
    CAMPOS_META,
    base_url_do_provedor,
    campos_do_provedor,
    ids_modelos_permitidos,
    lista_provedores,
    modelos_do_provedor,
    modelos_padrao,
    normalizar_modelos_salvos,
)


def _valores_formulario(request) -> dict:
    """Valores para reexibir o formulário após erro."""
    valores = {k: request.POST.get(k, '') for k in request.POST.keys()}
    valores['models'] = request.POST.getlist('models')
    valores.pop('api_key', None)
    return valores


def _extrair_payload(request, provider: str, *, exigindo_api_key: bool):
    """Valida POST e devolve (name, credentials_dict, erros).

    base_url vem sempre do catálogo do sistema.
    models só aceita ids liberados para o provedor.
    """
    erros = []
    fields = campos_do_provedor(provider)
    if not fields:
        return '', {}, ['Provedor inválido.']

    name = (request.POST.get('name') or '').strip()
    if not name:
        erros.append('Informe o nome da integração.')

    credentials = {}
    for field in fields:
        fname = field['name']
        if fname in CAMPOS_META:
            continue
        valor = (request.POST.get(fname) or '').strip()
        if valor:
            credentials[fname] = valor

    api_key = (credentials.get('api_key') or '').strip()
    if exigindo_api_key and not api_key:
        erros.append('Informe a API Key.')

    # URL definida pelo sistema — nunca vem do usuário
    credentials['base_url'] = base_url_do_provedor(provider)

    permitidos = ids_modelos_permitidos(provider)
    selecionados = [
        m.strip()
        for m in request.POST.getlist('models')
        if m and m.strip() in permitidos
    ]
    if not selecionados:
        erros.append('Selecione ao menos um modelo permitido pelo sistema.')
    else:
        credentials['models'] = selecionados

    return name, credentials, erros


class IAListView(ModuloObrigatorioMixin, ListView):
    model = IntegracaoIA
    template_name = 'integracoes/ia_list.html'
    context_object_name = 'integracoes'
    modulo_obrigatorio = MODULO_INTEGRACOES

    def get_queryset(self):
        return IntegracaoIA.objects.all().order_by('-is_active', 'name')


class IAWizardCreateView(ModuloObrigatorioMixin, View):
    """Modal wizard: passo 1 provedor, passo 2 credenciais."""
    modulo_obrigatorio = MODULO_INTEGRACOES

    def get(self, request):
        if not request.headers.get('HX-Request'):
            return redirect('integracoes:ia_list')
        return render(request, 'integracoes/_ia_wizard_modal.html', {
            'provedores': lista_provedores(),
            'modo': 'create',
            'form_action': reverse('integracoes:ia_create'),
            'modelos_selecionados': {},
        })

    def post(self, request):
        provider = (request.POST.get('provider') or '').strip()
        if provider not in IntegracaoIA.Provider.values:
            return render(request, 'integracoes/_ia_wizard_modal.html', {
                'provedores': lista_provedores(),
                'modo': 'create',
                'form_action': reverse('integracoes:ia_create'),
                'erro': 'Selecione um provedor de IA.',
                'provider_selecionado': provider,
                'modelos_selecionados': {},
            }, status=422)

        name, credentials, erros = _extrair_payload(request, provider, exigindo_api_key=True)
        if erros:
            return render(request, 'integracoes/_ia_wizard_modal.html', {
                'provedores': lista_provedores(),
                'modo': 'create',
                'form_action': reverse('integracoes:ia_create'),
                'erro': ' '.join(erros),
                'provider_selecionado': provider,
                'valores': _valores_formulario(request),
                'modelos_selecionados': {provider: request.POST.getlist('models')},
            }, status=422)

        obj = IntegracaoIA(name=name, provider=provider, created_by=request.user)
        obj.set_credentials(credentials)
        obj.save()

        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.CREATED,
            descricao=f'Integração IA "{obj.name}" ({obj.get_provider_display()}) criada.',
            actor=request.user,
            obj=obj,
            metadata={'provider': obj.provider},
        )
        messages.success(request, f'Integração "{obj.name}" criada com sucesso.')
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('integracoes:ia_list')
        return response


class IAUpdateView(ModuloObrigatorioMixin, View):
    """Edição em um passo (provedor fixo)."""
    modulo_obrigatorio = MODULO_INTEGRACOES

    def get(self, request, pk):
        if not request.headers.get('HX-Request'):
            return redirect('integracoes:ia_list')
        integracao = get_object_or_404(IntegracaoIA, pk=pk)
        creds = integracao.get_credentials()
        valores = {'name': integracao.name, **creds}
        valores.pop('api_key', None)
        modelos_sel = normalizar_modelos_salvos(creds) or modelos_padrao(integracao.provider)
        return render(request, 'integracoes/_ia_edit_modal.html', {
            'integracao': integracao,
            'campos': campos_do_provedor(integracao.provider),
            'modelos': modelos_do_provedor(integracao.provider),
            'modelos_selecionados': modelos_sel,
            'valores': valores,
            'form_action': reverse('integracoes:ia_update', args=[pk]),
        })

    def post(self, request, pk):
        integracao = get_object_or_404(IntegracaoIA, pk=pk)
        name, credentials, erros = _extrair_payload(
            request, integracao.provider, exigindo_api_key=False,
        )
        atual = integracao.get_credentials()
        if not credentials.get('api_key'):
            if atual.get('api_key'):
                credentials['api_key'] = atual['api_key']
            else:
                erros.append('Informe a API Key.')

        # Remove campo legado "model" (texto livre)
        credentials.pop('model', None)

        if erros:
            valores_erro = _valores_formulario(request)
            valores_erro['name'] = name or request.POST.get('name', '')
            return render(request, 'integracoes/_ia_edit_modal.html', {
                'integracao': integracao,
                'campos': campos_do_provedor(integracao.provider),
                'modelos': modelos_do_provedor(integracao.provider),
                'modelos_selecionados': request.POST.getlist('models'),
                'valores': valores_erro,
                'erro': ' '.join(erros),
                'form_action': reverse('integracoes:ia_update', args=[pk]),
            }, status=422)

        integracao.name = name
        integracao.set_credentials(credentials)
        integracao.save()
        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.UPDATED,
            descricao=f'Integração IA "{integracao.name}" atualizada.',
            actor=request.user,
            obj=integracao,
            metadata={'provider': integracao.provider},
        )
        messages.success(request, f'Integração "{integracao.name}" atualizada.')
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('integracoes:ia_list')
        return response


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_toggle_active(request, pk):
    integracao = get_object_or_404(IntegracaoIA, pk=pk)
    integracao.is_active = not integracao.is_active
    integracao.save(update_fields=['is_active', 'updated_at'])
    estado = 'ativada' if integracao.is_active else 'desativada'
    registrar_acao(
        modulo=MODULO_CORE,
        acao=(
            RegistroAcao.AcaoChoices.ACTIVATED
            if integracao.is_active
            else RegistroAcao.AcaoChoices.DEACTIVATED
        ),
        descricao=f'Integração IA "{integracao.name}" {estado}.',
        actor=request.user,
        obj=integracao,
        metadata={'provider': integracao.provider, 'is_active': integracao.is_active},
    )
    messages.success(request, f'Integração "{integracao.name}" {estado}.')
    return redirect('integracoes:ia_list')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_delete(request, pk):
    integracao = get_object_or_404(IntegracaoIA, pk=pk)
    nome = integracao.name
    provider = integracao.provider
    pk_antigo = integracao.pk
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.DELETED,
        descricao=f'Integração IA "{nome}" removida.',
        actor=request.user,
        obj=integracao,
        metadata={'provider': provider, 'pk': pk_antigo},
    )
    integracao.delete()
    messages.success(request, f'Integração "{nome}" removida.')
    return redirect('integracoes:ia_list')
