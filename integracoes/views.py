"""Views da listagem e wizard de integrações IA e APIs externas."""

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
from integracoes.api_providers import (
    CAMPOS_META_API,
    campos_do_provedor_api,
    default_base_url_api,
    lista_provedores_api,
)
from integracoes.models import IntegracaoApi, IntegracaoIA, TokenApiExterna
from integracoes.token_api import criar_token, usuario_pode_token_api
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
        modelos_sel = (
            normalizar_modelos_salvos(creds, integracao.provider)
            or modelos_padrao(integracao.provider)
        )
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


# ---------------------------------------------------------------------------
# Integrações de API externa (MoneyConsig, etc.)
# ---------------------------------------------------------------------------


def _valores_formulario_api(request) -> dict:
    valores = {k: request.POST.get(k, '') for k in request.POST.keys()}
    valores.pop('api_token', None)
    return valores


def _extrair_payload_api(request, provider: str, *, exigindo_token: bool):
    """Valida POST e devolve (name, credentials_dict, erros)."""
    erros = []
    fields = campos_do_provedor_api(provider)
    if not fields:
        return '', {}, ['Provedor inválido.']

    name = (request.POST.get('name') or '').strip()
    if not name:
        erros.append('Informe o nome da integração.')

    credentials = {}
    for field in fields:
        fname = field['name']
        if fname in CAMPOS_META_API:
            continue
        valor = (request.POST.get(fname) or '').strip()
        if valor:
            credentials[fname] = valor
        elif field.get('default') and fname == 'base_url':
            credentials[fname] = field['default']

    api_token = (credentials.get('api_token') or '').strip()
    if exigindo_token and not api_token:
        erros.append('Informe o Token Bearer.')

    from integracoes.moneyconsig_client import normalizar_base_url

    base_url = (credentials.get('base_url') or '').strip().rstrip('/')
    if not base_url:
        base_url = default_base_url_api(provider)
    if not base_url:
        erros.append('Informe a URL base.')
    else:
        credentials['base_url'] = normalizar_base_url(base_url)

    return name, credentials, erros


class ApiListView(ModuloObrigatorioMixin, ListView):
    model = IntegracaoApi
    template_name = 'integracoes/api_list.html'
    context_object_name = 'integracoes'
    modulo_obrigatorio = MODULO_INTEGRACOES

    def get_queryset(self):
        return IntegracaoApi.objects.all().order_by('-is_active', 'name')


class ApiWizardCreateView(ModuloObrigatorioMixin, View):
    """Modal wizard: passo 1 provedor, passo 2 credenciais."""
    modulo_obrigatorio = MODULO_INTEGRACOES

    def get(self, request):
        if not request.headers.get('HX-Request'):
            return redirect('integracoes:api_list')
        return render(request, 'integracoes/_api_wizard_modal.html', {
            'provedores': lista_provedores_api(),
            'modo': 'create',
            'form_action': reverse('integracoes:api_create'),
        })

    def post(self, request):
        provider = (request.POST.get('provider') or '').strip()
        if provider not in IntegracaoApi.Provider.values:
            return render(request, 'integracoes/_api_wizard_modal.html', {
                'provedores': lista_provedores_api(),
                'modo': 'create',
                'form_action': reverse('integracoes:api_create'),
                'erro': 'Selecione um provedor de API.',
                'provider_selecionado': provider,
            }, status=422)

        name, credentials, erros = _extrair_payload_api(
            request, provider, exigindo_token=True,
        )
        if erros:
            return render(request, 'integracoes/_api_wizard_modal.html', {
                'provedores': lista_provedores_api(),
                'modo': 'create',
                'form_action': reverse('integracoes:api_create'),
                'erro': ' '.join(erros),
                'provider_selecionado': provider,
                'valores': _valores_formulario_api(request),
            }, status=422)

        obj = IntegracaoApi(name=name, provider=provider, created_by=request.user)
        obj.set_credentials(credentials)
        obj.save()

        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.CREATED,
            descricao=f'Integração API "{obj.name}" ({obj.get_provider_display()}) criada.',
            actor=request.user,
            obj=obj,
            metadata={'provider': obj.provider},
        )
        messages.success(request, f'Integração "{obj.name}" criada com sucesso.')
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('integracoes:api_list')
        return response


class ApiUpdateView(ModuloObrigatorioMixin, View):
    """Edição em um passo (provedor fixo)."""
    modulo_obrigatorio = MODULO_INTEGRACOES

    def get(self, request, pk):
        if not request.headers.get('HX-Request'):
            return redirect('integracoes:api_list')
        integracao = get_object_or_404(IntegracaoApi, pk=pk)
        creds = integracao.get_credentials()
        valores = {'name': integracao.name, **creds}
        valores.pop('api_token', None)
        return render(request, 'integracoes/_api_edit_modal.html', {
            'integracao': integracao,
            'campos': campos_do_provedor_api(integracao.provider),
            'valores': valores,
            'form_action': reverse('integracoes:api_update', args=[pk]),
        })

    def post(self, request, pk):
        integracao = get_object_or_404(IntegracaoApi, pk=pk)
        name, credentials, erros = _extrair_payload_api(
            request, integracao.provider, exigindo_token=False,
        )
        atual = integracao.get_credentials()
        if not credentials.get('api_token'):
            if atual.get('api_token'):
                credentials['api_token'] = atual['api_token']
            else:
                erros.append('Informe o Token Bearer.')

        if erros:
            valores_erro = _valores_formulario_api(request)
            valores_erro['name'] = name or request.POST.get('name', '')
            return render(request, 'integracoes/_api_edit_modal.html', {
                'integracao': integracao,
                'campos': campos_do_provedor_api(integracao.provider),
                'valores': valores_erro,
                'erro': ' '.join(erros),
                'form_action': reverse('integracoes:api_update', args=[pk]),
            }, status=422)

        integracao.name = name
        integracao.set_credentials(credentials)
        integracao.save()
        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.UPDATED,
            descricao=f'Integração API "{integracao.name}" atualizada.',
            actor=request.user,
            obj=integracao,
            metadata={'provider': integracao.provider},
        )
        messages.success(request, f'Integração "{integracao.name}" atualizada.')
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('integracoes:api_list')
        return response


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def api_toggle_active(request, pk):
    integracao = get_object_or_404(IntegracaoApi, pk=pk)
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
        descricao=f'Integração API "{integracao.name}" {estado}.',
        actor=request.user,
        obj=integracao,
        metadata={'provider': integracao.provider, 'is_active': integracao.is_active},
    )
    messages.success(request, f'Integração "{integracao.name}" {estado}.')
    return redirect('integracoes:api_list')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def api_delete(request, pk):
    integracao = get_object_or_404(IntegracaoApi, pk=pk)
    nome = integracao.name
    provider = integracao.provider
    pk_antigo = integracao.pk
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.DELETED,
        descricao=f'Integração API "{nome}" removida.',
        actor=request.user,
        obj=integracao,
        metadata={'provider': provider, 'pk': pk_antigo},
    )
    integracao.delete()
    messages.success(request, f'Integração "{nome}" removida.')
    return redirect('integracoes:api_list')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def api_testar(request, pk):
    """Testa conexão MoneyConsig via GET /api/b2b/auth/me/."""
    integracao = get_object_or_404(IntegracaoApi, pk=pk)
    if integracao.provider != IntegracaoApi.Provider.MONEYCONSIG:
        return render(request, 'integracoes/_api_teste_resultado.html', {
            'ok': False,
            'mensagem': 'Teste disponível apenas para MoneyConsig.',
            'integracao': integracao,
        })

    # Usa temporariamente esta integração mesmo se houver outra ativa
    # (auth_me pega a primeira ativa — se for outra, ainda valida o token cadastrado)
    from integracoes import moneyconsig_client as mc

    creds = integracao.get_credentials()
    token = (creds.get('api_token') or '').strip()
    base = mc.normalizar_base_url(creds.get('base_url') or mc.DEFAULT_BASE)
    if not token:
        return render(request, 'integracoes/_api_teste_resultado.html', {
            'ok': False,
            'mensagem': 'Token ausente nesta integração.',
            'integracao': integracao,
        })

    # Chamada direta com as credenciais desta linha (não depende de “primeira ativa”)
    import requests
    from urllib.parse import urljoin

    url = urljoin(base + '/', 'api/b2b/auth/me/')
    try:
        resp = requests.get(
            url,
            headers=mc._headers(token),
            timeout=mc.TIMEOUT,
        )
        data = resp.json() if resp.content else {}
    except Exception as exc:
        return render(request, 'integracoes/_api_teste_resultado.html', {
            'ok': False,
            'mensagem': f'Falha ao conectar: {exc}',
            'integracao': integracao,
        })

    if resp.status_code == 401:
        return render(request, 'integracoes/_api_teste_resultado.html', {
            'ok': False,
            'mensagem': 'Token inválido ou sem permissão B2B (HTTP 401).',
            'integracao': integracao,
        })
    if resp.status_code >= 400:
        return render(request, 'integracoes/_api_teste_resultado.html', {
            'ok': False,
            'mensagem': f'HTTP {resp.status_code}: {data.get("detail") or data.get("erro") or resp.reason}',
            'integracao': integracao,
        })

    nome = data.get('nome') or data.get('username') or '—'
    escopo = data.get('escopo_label') or data.get('escopo') or '—'
    return render(request, 'integracoes/_api_teste_resultado.html', {
        'ok': True,
        'mensagem': f'Conexão OK — {nome} · escopo {escopo}',
        'integracao': integracao,
        'detalhe': data,
    })


@requer_modulo(MODULO_INTEGRACOES)
def ia_aprendizado(request):
    """Página de aprendizado e flag do Assistente no Helpdesk."""
    from collections import Counter

    from django.core.paginator import Paginator
    from django.db.models import Count, Q

    from integracoes.memoria_chat import listar_conversas_usuario
    from integracoes.models import AssistenteChunk, AssistenteConfig, AssistenteInteracao
    from integracoes.regras_seed import garantir_chunks_regras

    garantir_chunks_regras()

    config = AssistenteConfig.get_solo()
    q = (request.GET.get('q') or '').strip()
    origem = (request.GET.get('origem') or '').strip().lower()
    categoria = (request.GET.get('categoria') or '').strip()
    ativo_filtro = (request.GET.get('ativo') or '1').strip().lower()
    eval_filtro = (request.GET.get('eval') or 'pendente').strip().lower()
    tab = (request.GET.get('tab') or 'chunks').strip().lower()
    if tab not in ('chunks', 'eval', 'config'):
        tab = 'chunks'

    qs = AssistenteChunk.objects.all()
    if ativo_filtro in ('1', 'true', 'sim'):
        qs = qs.filter(ativo=True)
    elif ativo_filtro in ('0', 'false', 'nao', 'não'):
        qs = qs.filter(ativo=False)
    # ativo=all → sem filtro

    if origem in {c.value for c in AssistenteChunk.Origem}:
        qs = qs.filter(origem=origem)
    if categoria:
        qs = qs.filter(categoria_hint__icontains=categoria)
    if q:
        qs = qs.filter(
            Q(titulo__icontains=q) | Q(conteudo__icontains=q) | Q(categoria_hint__icontains=q)
        )

    paginator = Paginator(qs.order_by('-atualizado_em', '-criado_em'), 20)
    page_obj = paginator.get_page(request.GET.get('page') or 1)

    contagens = {
        'total': AssistenteChunk.objects.count(),
        'ativos': AssistenteChunk.objects.filter(ativo=True).count(),
        'inativos': AssistenteChunk.objects.filter(ativo=False).count(),
    }
    por_origem = {
        row['origem']: row['n']
        for row in AssistenteChunk.objects.values('origem').annotate(n=Count('id'))
    }
    por_origem_curadoria = int(por_origem.get('manual') or 0) + int(por_origem.get('chat') or 0)

    # Eval: últimas interações + contadores
    interacoes_qs = AssistenteInteracao.objects.all()
    eval_contagens = {
        'total': AssistenteInteracao.objects.count(),
        'pendentes': AssistenteInteracao.objects.filter(nota__isnull=True).count(),
        'uteis': AssistenteInteracao.objects.filter(nota=AssistenteInteracao.Nota.UTIL).count(),
        'ruins': AssistenteInteracao.objects.filter(nota=AssistenteInteracao.Nota.RUIM).count(),
    }
    avaliadas = eval_contagens['uteis'] + eval_contagens['ruins']
    eval_contagens['pct_util'] = (
        round(100 * eval_contagens['uteis'] / avaliadas) if avaliadas else None
    )

    if eval_filtro == 'pendente':
        interacoes_qs = interacoes_qs.filter(nota__isnull=True)
    elif eval_filtro == 'util':
        interacoes_qs = interacoes_qs.filter(nota=AssistenteInteracao.Nota.UTIL)
    elif eval_filtro == 'ruim':
        interacoes_qs = interacoes_qs.filter(nota=AssistenteInteracao.Nota.RUIM)
    # eval=all → sem filtro

    interacoes = list(interacoes_qs.order_by('-criado_em')[:30])
    todos_chunk_ids = []
    for it in interacoes:
        todos_chunk_ids.extend(it.chunk_ids or [])
    titulos_map = {
        c.pk: c.titulo
        for c in AssistenteChunk.objects.filter(pk__in=set(todos_chunk_ids)).only('id', 'titulo')
    }
    for it in interacoes:
        it.chunks_resumo = [
            {'id': cid, 'titulo': titulos_map.get(cid, f'#{cid}')}
            for cid in (it.chunk_ids or [])[:8]
        ]

    # Chunks mais presentes em interações ruins (ajuda a curar memória)
    ruins = AssistenteInteracao.objects.filter(
        nota=AssistenteInteracao.Nota.RUIM,
    ).order_by('-criado_em')[:120]
    counter = Counter()
    for it in ruins:
        for cid in (it.chunk_ids or []):
            try:
                counter[int(cid)] += 1
            except (TypeError, ValueError):
                continue
    top_ruins = counter.most_common(8)
    titulos_ruins = {
        c.pk: c.titulo
        for c in AssistenteChunk.objects.filter(pk__in=[i for i, _ in top_ruins]).only('id', 'titulo')
    }
    chunks_ruins = [
        {'id': cid, 'titulo': titulos_ruins.get(cid, f'#{cid}'), 'n': n}
        for cid, n in top_ruins
    ]

    integracoes = IntegracaoIA.objects.filter(is_active=True).order_by('name')
    from integracoes.memoria_chat import listar_conversas_usuario
    from integracoes.models import AssistenteMemoriaConversa

    conversas = listar_conversas_usuario(request.user)
    conversa_ativa = None
    conversa_id = request.GET.get('conversa')
    if conversa_id:
        conversa_ativa = AssistenteMemoriaConversa.objects.filter(
            pk=conversa_id, user=request.user, ativo=True,
        ).first()
    if conversa_ativa is None and conversas:
        conversa_ativa = AssistenteMemoriaConversa.objects.filter(
            pk=conversas[0]['id'], user=request.user, ativo=True,
        ).first()
    chat_historico = list(conversa_ativa.mensagens) if conversa_ativa else []
    from integracoes.llm import obter_integracao_embedding
    return render(request, 'integracoes/ia_aprendizado.html', {
        'config': config,
        'chunks': page_obj,
        'page_obj': page_obj,
        'filtros': {
            'q': q,
            'origem': origem,
            'categoria': categoria,
            'ativo': ativo_filtro,
            'eval': eval_filtro,
            'tab': tab,
        },
        'tab': tab,
        'contagens': contagens,
        'por_origem': por_origem,
        'por_origem_curadoria': por_origem_curadoria,
        'integracoes': integracoes,
        'chat_historico': chat_historico,
        'conversas_memoria': conversas,
        'conversa_ativa_id': conversa_ativa.pk if conversa_ativa else None,
        'interacoes': interacoes,
        'eval_contagens': eval_contagens,
        'chunks_ruins': chunks_ruins,
        'embeddings_disponivel': bool(obter_integracao_embedding()),
    })


def _redirect_aprendizado(request, anchor: str = '', tab: str = ''):
    """Volta à lista preservando filtros GET (via next ou Referer query)."""
    from django.urls import reverse
    from urllib.parse import urlencode

    next_url = (request.POST.get('next') or '').strip()
    if next_url.startswith('/'):
        return redirect(next_url + (f'#{anchor}' if anchor else ''))
    base = reverse('integracoes:ia_aprendizado')
    params = {}
    for key in ('q', 'origem', 'categoria', 'ativo', 'page', 'tab', 'eval'):
        val = (request.POST.get(f'filtro_{key}') or '').strip()
        if val:
            params[key] = val
    tab_final = (tab or params.get('tab') or '').strip().lower()
    if tab_final in ('chunks', 'eval', 'config'):
        params['tab'] = tab_final
    qs = urlencode(params)
    url = f'{base}?{qs}' if qs else base
    if anchor:
        url = f'{url}#{anchor}'
    return redirect(url)


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_aprendizado_toggle(request):
    from integracoes.models import AssistenteConfig

    config = AssistenteConfig.get_solo()
    config.ativo = request.POST.get('ativo') in ('1', 'true', 'on', 'yes')
    integracao_id = (request.POST.get('integracao') or '').strip()
    if integracao_id.isdigit():
        config.integracao_id = int(integracao_id)
    elif integracao_id == '':
        config.integracao = None
    visao_id = (request.POST.get('integracao_visao') or '').strip()
    if visao_id.isdigit():
        config.integracao_visao_id = int(visao_id)
    elif visao_id == '':
        config.integracao_visao = None
    config.save()
    estado = 'ativado' if config.ativo else 'desativado'
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=f'Assistente Helpdesk {estado}.',
        actor=request.user,
        metadata={'assistente_ativo': config.ativo},
    )
    messages.success(request, f'Assistente no Helpdesk {estado}.')
    return _redirect_aprendizado(request, tab='config')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_aprendizado_gerar(request):
    from datetime import datetime

    from integracoes.assistente_runtime import gerar_chunks_aprendizado
    from integracoes.llm import LlmError

    def _parse_date(raw):
        raw = (raw or '').strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, '%Y-%m-%d').date()
        except ValueError:
            return None

    data_inicio = _parse_date(request.POST.get('data_inicio'))
    data_fim = _parse_date(request.POST.get('data_fim'))
    try:
        limite = int(request.POST.get('limite') or 30)
    except (TypeError, ValueError):
        limite = 30

    try:
        resultado = gerar_chunks_aprendizado(
            limite_tickets=limite,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.CREATED,
            descricao=(
                f'Aprendizado IA gerou {resultado["chunks"]} chunks '
                f'a partir de {resultado["tickets_analisados"]} chamados.'
            ),
            actor=request.user,
            metadata={
                **resultado,
                'data_inicio': str(data_inicio) if data_inicio else None,
                'data_fim': str(data_fim) if data_fim else None,
                'limite': limite,
            },
        )
        preservados = resultado.get('preservados_curadoria', 0)
        periodo = ''
        if data_inicio or data_fim:
            periodo = f' Período {data_inicio or "…"} → {data_fim or "…"}.'
        messages.success(
            request,
            f'Aprendizado gerado: {resultado["chunks"]} chunks IA '
            f'({resultado["tickets_analisados"]} chamados).{periodo} '
            f'Preservados {preservados} chunks manuais/chat.',
        )
    except LlmError as exc:
        messages.error(request, f'Falha ao gerar aprendizado: {exc}')
    except Exception:
        messages.error(request, 'Erro inesperado ao gerar aprendizado.')
    return _redirect_aprendizado(request, tab='config')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_chunk_update(request, pk):
    from integracoes.models import AssistenteChunk

    chunk = get_object_or_404(AssistenteChunk, pk=pk)
    titulo = (request.POST.get('titulo') or '').strip()
    conteudo = (request.POST.get('conteudo') or '').strip()
    categoria = (request.POST.get('categoria_hint') or '').strip()
    if not titulo or not conteudo:
        messages.error(request, 'Título e conteúdo são obrigatórios.')
        return _redirect_aprendizado(request, anchor=f'chunk-{pk}')
    chunk.titulo = titulo[:200]
    chunk.conteudo = conteudo
    chunk.categoria_hint = categoria[:120]
    chunk.save(update_fields=['titulo', 'conteudo', 'categoria_hint', 'atualizado_em'])
    from integracoes.embeddings import atualizar_embedding_chunk
    atualizar_embedding_chunk(chunk)
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=f'Chunk de aprendizado "{chunk.titulo}" corrigido.',
        actor=request.user,
        metadata={'chunk_id': chunk.pk},
    )
    messages.success(request, f'Chunk "{chunk.titulo}" atualizado.')
    return _redirect_aprendizado(request, anchor=f'chunk-{pk}')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_chunk_create(request):
    from integracoes.models import AssistenteChunk

    titulo = (request.POST.get('titulo') or '').strip()
    conteudo = (request.POST.get('conteudo') or '').strip()
    categoria = (request.POST.get('categoria_hint') or '').strip()
    if not titulo or not conteudo:
        messages.error(request, 'Título e conteúdo são obrigatórios.')
        return _redirect_aprendizado(request, tab='chunks')
    chunk = AssistenteChunk.objects.create(
        titulo=titulo[:200],
        conteudo=conteudo,
        categoria_hint=categoria[:120],
        fonte_ticket_ids=[],
        origem=AssistenteChunk.Origem.MANUAL,
        ativo=True,
        tags=[],
    )
    from integracoes.embeddings import atualizar_embedding_chunk
    atualizar_embedding_chunk(chunk)
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.CREATED,
        descricao=f'Chunk de aprendizado "{chunk.titulo}" criado manualmente.',
        actor=request.user,
        metadata={'chunk_id': chunk.pk},
    )
    messages.success(request, f'Chunk "{chunk.titulo}" criado.')
    return _redirect_aprendizado(request, anchor=f'chunk-{chunk.pk}', tab='chunks')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_chunk_toggle_ativo(request, pk):
    from integracoes.models import AssistenteChunk

    chunk = get_object_or_404(AssistenteChunk, pk=pk)
    chunk.ativo = not chunk.ativo
    chunk.save(update_fields=['ativo', 'atualizado_em'])
    estado = 'ativado' if chunk.ativo else 'desativado'
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=f'Chunk "{chunk.titulo}" {estado}.',
        actor=request.user,
        metadata={'chunk_id': chunk.pk, 'ativo': chunk.ativo},
    )
    messages.success(request, f'Chunk "{chunk.titulo}" {estado}.')
    return _redirect_aprendizado(request, anchor=f'chunk-{pk}')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_embeddings_recalcular(request):
    """Recalcula embeddings pendentes dos chunks ativos (ChatGPT)."""
    from integracoes.embeddings import recalcular_embeddings

    resultado = recalcular_embeddings(so_pendentes=True, limite=80)
    if not resultado.get('ok'):
        messages.error(request, resultado.get('error') or 'Falha ao recalcular embeddings.')
        return _redirect_aprendizado(request, tab='config')
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=(
            f'Recálculo de embeddings: {resultado["ok_count"]} ok, '
            f'{resultado["fail_count"]} falhas.'
        ),
        actor=request.user,
        metadata=resultado,
    )
    messages.success(
        request,
        f'Embeddings: {resultado["ok_count"]} atualizados, '
        f'{resultado["fail_count"]} falhas '
        f'(modelo {resultado.get("modelo") or "-"}).',
    )
    return _redirect_aprendizado(request, tab='config')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_interacao_nota(request, pk):
    """Feedback da TI: útil (1) ou ruim (-1) em uma rodada do Assistente."""
    from django.utils import timezone

    from integracoes.models import AssistenteInteracao

    interacao = get_object_or_404(AssistenteInteracao, pk=pk)
    raw = (request.POST.get('nota') or '').strip()
    try:
        nota = int(raw)
    except (TypeError, ValueError):
        messages.error(request, 'Nota inválida.')
        return _redirect_aprendizado(request, tab='eval', anchor='eval-panel')
    if nota not in (
        AssistenteInteracao.Nota.UTIL,
        AssistenteInteracao.Nota.RUIM,
    ):
        messages.error(request, 'Nota deve ser útil ou ruim.')
        return _redirect_aprendizado(request, tab='eval', anchor='eval-panel')

    interacao.nota = nota
    interacao.nota_por = request.user
    interacao.nota_em = timezone.now()
    interacao.comentario = (request.POST.get('comentario') or '').strip()[:400]
    interacao.save(update_fields=['nota', 'nota_por', 'nota_em', 'comentario'])
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.UPDATED,
        descricao=(
            f'Eval Assistente ticket #{interacao.ticket_id}: '
            f'{"útil" if nota == 1 else "ruim"}.'
        ),
        actor=request.user,
        metadata={'interacao_id': interacao.pk, 'nota': nota},
    )
    messages.success(
        request,
        f'Interação #{interacao.pk} marcada como {"útil" if nota == 1 else "ruim"}.',
    )
    eval_q = (request.POST.get('filtro_eval') or 'pendente').strip()
    from django.urls import reverse
    from urllib.parse import urlencode
    url = reverse('integracoes:ia_aprendizado') + '?' + urlencode({
        'tab': 'eval',
        'eval': eval_q,
    })
    return redirect(url + '#eval-panel')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_chunk_delete(request, pk):
    from integracoes.models import AssistenteChunk

    chunk = get_object_or_404(AssistenteChunk, pk=pk)
    titulo = chunk.titulo
    chunk.delete()
    registrar_acao(
        modulo=MODULO_CORE,
        acao=RegistroAcao.AcaoChoices.DELETED,
        descricao=f'Chunk de aprendizado "{titulo}" removido.',
        actor=request.user,
        metadata={'chunk_id': pk},
    )
    messages.success(request, f'Chunk "{titulo}" removido.')
    return _redirect_aprendizado(request)


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_aprendizado_chat(request):
    """Chat para gravar/corrigir memória (chunks) conversando com a IA."""
    import json

    from django.http import JsonResponse

    from integracoes.llm import LlmError
    from integracoes.markdown_safe import render_markdown_leve
    from integracoes.memoria_chat import processar_mensagem_conversa

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    mensagem = (body.get('message') or request.POST.get('message') or '').strip()
    if not mensagem:
        return JsonResponse({'ok': False, 'error': 'Mensagem vazia.'}, status=400)

    conversa_id = body.get('conversa_id') or request.POST.get('conversa_id')
    try:
        resultado = processar_mensagem_conversa(request.user, mensagem, conversa_id)
    except LlmError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=502)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Erro ao processar o chat.'}, status=500)

    if resultado.get('memoria_alterada'):
        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.UPDATED,
            descricao='Memória do Assistente atualizada via chat de aprendizado.',
            actor=request.user,
            metadata={
                'via': 'chat_memoria',
                'conversa_id': resultado.get('conversa_id'),
            },
        )

    return JsonResponse({
        'ok': True,
        'reply': resultado['reply'],
        'reply_html': render_markdown_leve(resultado['reply'] or ''),
        'memoria_alterada': resultado['memoria_alterada'],
        'conversa_id': resultado.get('conversa_id'),
        'titulo': resultado.get('titulo') or '',
    })


@requer_modulo(MODULO_INTEGRACOES)
def ia_aprendizado_conversas(request):
    """Lista conversas de memória do usuário (JSON)."""
    from django.http import JsonResponse

    from integracoes.memoria_chat import listar_conversas_usuario

    return JsonResponse({
        'ok': True,
        'results': listar_conversas_usuario(request.user),
    })


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_aprendizado_conversa_nova(request):
    """Cria uma nova conversa vazia."""
    from django.http import JsonResponse

    from integracoes.memoria_chat import obter_ou_criar_conversa

    conv = obter_ou_criar_conversa(request.user, conversa_id=None)
    return JsonResponse({
        'ok': True,
        'conversa_id': conv.pk,
        'titulo': conv.titulo,
        'mensagens': [],
    })


@requer_modulo(MODULO_INTEGRACOES)
def ia_aprendizado_conversa_get(request, pk):
    """Retorna mensagens de uma conversa do usuário."""
    from django.http import JsonResponse

    from integracoes.markdown_safe import render_markdown_leve
    from integracoes.models import AssistenteMemoriaConversa

    conv = get_object_or_404(
        AssistenteMemoriaConversa, pk=pk, user=request.user, ativo=True,
    )
    mensagens = []
    for m in (conv.mensagens or []):
        item = {
            'role': m.get('role'),
            'content': m.get('content') or '',
        }
        if item['role'] == 'assistant':
            item['content_html'] = render_markdown_leve(item['content'])
        mensagens.append(item)
    return JsonResponse({
        'ok': True,
        'conversa_id': conv.pk,
        'titulo': conv.titulo,
        'mensagens': mensagens,
    })


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_aprendizado_chat_limpar(request):
    """Arquiva a conversa ativa (ou cria histórico limpo)."""
    import json

    from django.http import JsonResponse

    from integracoes.models import AssistenteMemoriaConversa

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    conversa_id = body.get('conversa_id') or request.POST.get('conversa_id')
    if conversa_id:
        AssistenteMemoriaConversa.objects.filter(
            pk=conversa_id, user=request.user, ativo=True,
        ).update(ativo=False)
    return JsonResponse({'ok': True})


# ---------------------------------------------------------------------------
# Tokens de API externa (integração CRM-TI → sistemas do cliente)
# ---------------------------------------------------------------------------


def resposta_sem_permissao_token(request):
    from django.http import HttpResponseForbidden, JsonResponse
    from django.shortcuts import redirect

    if request.headers.get('HX-Request'):
        return HttpResponseForbidden('Sem permissão para gerar tokens de API.')
    if request.content_type == 'application/json':
        return JsonResponse({'error': 'Sem permissão para gerar tokens de API.'}, status=403)
    return redirect('sem_permissao')


class TokenListView(ModuloObrigatorioMixin, ListView):
    model = TokenApiExterna
    template_name = 'integracoes/tokens_list.html'
    context_object_name = 'tokens'
    modulo_obrigatorio = MODULO_INTEGRACOES

    def get(self, request, *args, **kwargs):
        if not usuario_pode_token_api(request.user):
            return resposta_sem_permissao_token(request)
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        return (
            TokenApiExterna.objects.filter(user=self.request.user)
            .order_by('-ativo', '-criado_em')
        )


class TokenGerarView(ModuloObrigatorioMixin, View):
    """GET: modal formulário · POST: gera token e mostra plaintext uma vez."""
    modulo_obrigatorio = MODULO_INTEGRACOES

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not usuario_pode_token_api(request.user):
            return resposta_sem_permissao_token(request)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        if not request.headers.get('HX-Request'):
            return redirect('integracoes:tokens_list')
        return render(request, 'integracoes/_token_gerar_modal.html', {
            'form_action': reverse('integracoes:tokens_gerar'),
        })

    def post(self, request):
        nome = (request.POST.get('nome') or '').strip()
        try:
            token_obj, plaintext = criar_token(request.user, nome)
        except ValueError as exc:
            return render(request, 'integracoes/_token_gerar_modal.html', {
                'form_action': reverse('integracoes:tokens_gerar'),
                'erro': str(exc),
                'nome': nome,
            }, status=422)
        except PermissionError as exc:
            return render(request, 'integracoes/_token_gerar_modal.html', {
                'form_action': reverse('integracoes:tokens_gerar'),
                'erro': str(exc),
                'nome': nome,
            }, status=403)

        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.CREATED,
            descricao=f'Token API externa "{token_obj.nome}" gerado.',
            actor=request.user,
            obj=token_obj,
            metadata={'prefixo': token_obj.prefixo, 'pk': token_obj.pk},
        )
        return render(request, 'integracoes/_token_gerado_modal.html', {
            'token_obj': token_obj,
            'token_plaintext': plaintext,
        })


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def token_revogar(request, pk):
    """Desativa (revoga) um token do próprio usuário."""
    if not usuario_pode_token_api(request.user):
        return resposta_sem_permissao_token(request)

    token_obj = get_object_or_404(TokenApiExterna, pk=pk, user=request.user)
    if token_obj.ativo:
        token_obj.ativo = False
        token_obj.save(update_fields=['ativo'])
        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.UPDATED,
            descricao=f'Token API externa "{token_obj.nome}" revogado.',
            actor=request.user,
            obj=token_obj,
            metadata={'prefixo': token_obj.prefixo, 'pk': token_obj.pk},
        )
        messages.success(request, f'Token "{token_obj.nome}" revogado.')
    else:
        messages.info(request, f'Token "{token_obj.nome}" já estava revogado.')
    return redirect('integracoes:tokens_list')


@requer_modulo(MODULO_INTEGRACOES)
def tokens_docs_download(request):
    """Baixa documentação Markdown passo a passo da API (exemplo Python)."""
    from django.http import HttpResponse

    from integracoes.api_docs import montar_documentacao_api_python, nome_arquivo_docs

    if not usuario_pode_token_api(request.user):
        return resposta_sem_permissao_token(request)

    base_url = request.build_absolute_uri('/').rstrip('/')
    conteudo = montar_documentacao_api_python(
        base_url=base_url,
        username=request.user.username,
    )
    response = HttpResponse(conteudo, content_type='text/markdown; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nome_arquivo_docs()}"'
    return response

