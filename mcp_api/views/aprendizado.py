"""API MCP read-only: chunks de aprendizado do Assistente."""

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from integracoes.assistente_runtime import buscar_chunks
from integracoes.models import AssistenteChunk
from mcp_api.auth import requer_token_mcp
from mcp_api.serializers import parse_limit, serialize_chunk


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
