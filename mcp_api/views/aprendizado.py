"""API MCP: chunks de aprendizado do Assistente (leitura + escrita)."""

import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from integracoes.assistente_runtime import buscar_chunks
from integracoes.models import AssistenteChunk
from mcp_api.auth import requer_token_mcp
from mcp_api.serializers import parse_limit, serialize_chunk


def _json_body(request) -> dict:
    try:
        if request.body:
            return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
    return {k: v for k, v in request.POST.items()}


def _parse_tags(raw) -> list:
    if isinstance(raw, list):
        return [str(t).strip()[:40] for t in raw if str(t).strip()][:12]
    if isinstance(raw, str) and raw.strip():
        return [p.strip()[:40] for p in raw.split(',') if p.strip()][:12]
    return []


@require_GET
@requer_token_mcp
def list_chunks(request):
    """Lista chunks ativos (preview). Filtros: origem, limit."""
    limite = parse_limit(request, default=30)
    qs = AssistenteChunk.objects.filter(ativo=True)
    origem = (request.GET.get('origem') or '').strip().lower()
    if origem in {c.value for c in AssistenteChunk.Origem}:
        qs = qs.filter(origem=origem)
    itens = [serialize_chunk(c, detalhe=False) for c in qs[:limite]]
    return JsonResponse({'ok': True, 'count': len(itens), 'results': itens})


@require_GET
@requer_token_mcp
def get_chunk(request, pk):
    """Detalhe de um chunk (conteúdo completo)."""
    chunk = get_object_or_404(AssistenteChunk, pk=pk)
    return JsonResponse({'ok': True, 'chunk': serialize_chunk(chunk, detalhe=True)})


@require_GET
@requer_token_mcp
def search_chunks(request):
    """Busca chunks por relevância textual (mesmo score do Assistente)."""
    q = (request.GET.get('q') or '').strip()
    limite = parse_limit(request, default=20)
    so_ativos = (request.GET.get('ativos') or '1').strip().lower() not in ('0', 'false', 'no')
    chunks = buscar_chunks(q=q, limite=limite, so_ativos=so_ativos)
    itens = [serialize_chunk(c, detalhe=False) for c in chunks]
    return JsonResponse({'ok': True, 'q': q, 'count': len(itens), 'results': itens})


@csrf_exempt
@require_http_methods(['POST'])
@requer_token_mcp
def create_chunk(request):
    """Cria chunk manual (origem=manual). Body: titulo, conteudo, categoria_hint?, tags?"""
    body = _json_body(request)
    titulo = (body.get('titulo') or '').strip()
    conteudo = (body.get('conteudo') or '').strip()
    if not titulo or not conteudo:
        return JsonResponse({'ok': False, 'error': 'titulo e conteudo obrigatórios'}, status=400)
    chunk = AssistenteChunk.objects.create(
        titulo=titulo[:200],
        conteudo=conteudo,
        categoria_hint=(body.get('categoria_hint') or '').strip()[:120],
        fonte_ticket_ids=[],
        origem=AssistenteChunk.Origem.MANUAL,
        ativo=True,
        tags=_parse_tags(body.get('tags')),
    )
    from integracoes.embeddings import atualizar_embedding_chunk
    atualizar_embedding_chunk(chunk)
    return JsonResponse({'ok': True, 'chunk': serialize_chunk(chunk, detalhe=True)}, status=201)


@csrf_exempt
@require_http_methods(['POST'])
@requer_token_mcp
def update_chunk(request, pk):
    """Atualiza chunk. Body: titulo?, conteudo?, categoria_hint?, tags?, ativo?"""
    chunk = get_object_or_404(AssistenteChunk, pk=pk)
    body = _json_body(request)
    if 'titulo' in body and body.get('titulo') is not None:
        t = str(body.get('titulo') or '').strip()
        if not t:
            return JsonResponse({'ok': False, 'error': 'titulo vazio'}, status=400)
        chunk.titulo = t[:200]
    if 'conteudo' in body and body.get('conteudo') is not None:
        c = str(body.get('conteudo') or '').strip()
        if not c:
            return JsonResponse({'ok': False, 'error': 'conteudo vazio'}, status=400)
        chunk.conteudo = c
    if 'categoria_hint' in body and body.get('categoria_hint') is not None:
        chunk.categoria_hint = str(body.get('categoria_hint') or '').strip()[:120]
    if 'tags' in body:
        chunk.tags = _parse_tags(body.get('tags'))
    if 'ativo' in body:
        raw = body.get('ativo')
        if isinstance(raw, bool):
            chunk.ativo = raw
        else:
            chunk.ativo = str(raw).strip().lower() in ('1', 'true', 'yes', 'sim')
    chunk.save()
    from integracoes.embeddings import atualizar_embedding_chunk
    atualizar_embedding_chunk(chunk)
    return JsonResponse({'ok': True, 'chunk': serialize_chunk(chunk, detalhe=True)})
