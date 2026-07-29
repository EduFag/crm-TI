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


@requer_modulo(MODULO_INTEGRACOES)
def ia_aprendizado(request):
    """Página de aprendizado e flag do Assistente no Helpdesk."""
    from collections import Counter

    from django.core.paginator import Paginator
    from django.db.models import Count, Q

    from integracoes.memoria_chat import SESSION_KEY
    from integracoes.models import AssistenteChunk, AssistenteConfig, AssistenteInteracao
    from integracoes.regras_seed import garantir_chunks_regras

    garantir_chunks_regras()

    config = AssistenteConfig.get_solo()
    q = (request.GET.get('q') or '').strip()
    origem = (request.GET.get('origem') or '').strip().lower()
    categoria = (request.GET.get('categoria') or '').strip()
    ativo_filtro = (request.GET.get('ativo') or '1').strip().lower()
    eval_filtro = (request.GET.get('eval') or 'pendente').strip().lower()

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
    chat_historico = request.session.get(SESSION_KEY) or []
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
        },
        'contagens': contagens,
        'por_origem': por_origem,
        'integracoes': integracoes,
        'chat_historico': chat_historico,
        'interacoes': interacoes,
        'eval_contagens': eval_contagens,
        'chunks_ruins': chunks_ruins,
        'embeddings_disponivel': bool(obter_integracao_embedding()),
    })


def _redirect_aprendizado(request, anchor: str = ''):
    """Volta à lista preservando filtros GET (via next ou Referer query)."""
    from django.urls import reverse
    from urllib.parse import urlencode

    next_url = (request.POST.get('next') or '').strip()
    if next_url.startswith('/'):
        return redirect(next_url + (f'#{anchor}' if anchor else ''))
    base = reverse('integracoes:ia_aprendizado')
    params = {}
    for key in ('q', 'origem', 'categoria', 'ativo', 'page'):
        val = (request.POST.get(f'filtro_{key}') or '').strip()
        if val:
            params[key] = val
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
    return redirect('integracoes:ia_aprendizado')


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_aprendizado_gerar(request):
    from integracoes.assistente_runtime import gerar_chunks_aprendizado
    from integracoes.llm import LlmError

    try:
        resultado = gerar_chunks_aprendizado()
        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.CREATED,
            descricao=(
                f'Aprendizado IA gerou {resultado["chunks"]} chunks '
                f'a partir de {resultado["tickets_analisados"]} chamados.'
            ),
            actor=request.user,
            metadata=resultado,
        )
        preservados = resultado.get('preservados_curadoria', 0)
        messages.success(
            request,
            f'Aprendizado gerado: {resultado["chunks"]} chunks IA '
            f'({resultado["tickets_analisados"]} chamados). '
            f'Preservados {preservados} chunks manuais/chat.',
        )
    except LlmError as exc:
        messages.error(request, f'Falha ao gerar aprendizado: {exc}')
    except Exception:
        messages.error(request, 'Erro inesperado ao gerar aprendizado.')
    return redirect('integracoes:ia_aprendizado')


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
        return redirect('integracoes:ia_aprendizado')
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
    return redirect('integracoes:ia_aprendizado')


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
        return redirect('integracoes:ia_aprendizado')
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
    return redirect('integracoes:ia_aprendizado')


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
        return redirect('integracoes:ia_aprendizado')
    if nota not in (
        AssistenteInteracao.Nota.UTIL,
        AssistenteInteracao.Nota.RUIM,
    ):
        messages.error(request, 'Nota deve ser útil ou ruim.')
        return redirect('integracoes:ia_aprendizado')

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
    url = reverse('integracoes:ia_aprendizado') + '?' + urlencode({'eval': eval_q})
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
    from integracoes.memoria_chat import SESSION_KEY, processar_mensagem_memoria

    try:
        body = json.loads(request.body.decode('utf-8')) if request.body else {}
    except json.JSONDecodeError:
        body = {}
    mensagem = (body.get('message') or request.POST.get('message') or '').strip()
    if not mensagem:
        return JsonResponse({'ok': False, 'error': 'Mensagem vazia.'}, status=400)

    historico = request.session.get(SESSION_KEY) or []
    if not isinstance(historico, list):
        historico = []

    try:
        resultado = processar_mensagem_memoria(historico, mensagem)
    except LlmError as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=502)
    except Exception:
        return JsonResponse({'ok': False, 'error': 'Erro ao processar o chat.'}, status=500)

    request.session[SESSION_KEY] = resultado['historico']
    request.session.modified = True

    if resultado.get('memoria_alterada'):
        registrar_acao(
            modulo=MODULO_CORE,
            acao=RegistroAcao.AcaoChoices.UPDATED,
            descricao='Memória do Assistente atualizada via chat de aprendizado.',
            actor=request.user,
            metadata={'via': 'chat_memoria'},
        )

    return JsonResponse({
        'ok': True,
        'reply': resultado['reply'],
        'reply_html': render_markdown_leve(resultado['reply'] or ''),
        'memoria_alterada': resultado['memoria_alterada'],
    })


@requer_modulo(MODULO_INTEGRACOES)
@require_POST
def ia_aprendizado_chat_limpar(request):
    from django.http import JsonResponse

    from integracoes.memoria_chat import SESSION_KEY

    request.session[SESSION_KEY] = []
    request.session.modified = True
    return JsonResponse({'ok': True})
