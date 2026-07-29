"""Endpoints MCP read-only de operadores e WhatsApp."""

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from mcp_api.auth import requer_token_mcp
from mcp_api.serializers import parse_limit
from operadores.models import Operador, WhatsAppAccount


def _serialize_operador(op: Operador) -> dict:
    pa = op.pa
    ilha = pa.ilha if pa else None
    setor = ilha.setor if ilha else None
    return {
        'id': op.pk,
        'name': op.name,
        'pa': pa.name if pa else None,
        'ilha': ilha.name if ilha else None,
        'setor': setor.name if setor else None,
        'whatsapp_count': op.whatsapp_accounts.count(),
        'created_at': op.created_at.isoformat() if op.created_at else None,
        'updated_at': op.updated_at.isoformat() if op.updated_at else None,
    }


def _serialize_whatsapp(wa: WhatsAppAccount) -> dict:
    return {
        'id': wa.pk,
        'phone_number': wa.phone_number,
        'formatted_number': wa.formatted_number,
        'account_type': wa.account_type,
        'account_type_display': wa.get_account_type_display(),
        'status': wa.status,
        'status_display': wa.get_status_display(),
        'operador_id': wa.operador_id,
        'operador': wa.operador.name if wa.operador_id else None,
        'chip_id': wa.chip_id,
        'chip_line': wa.chip.line_number if wa.chip_id else None,
        'created_at': wa.created_at.isoformat() if wa.created_at else None,
        'updated_at': wa.updated_at.isoformat() if wa.updated_at else None,
    }


@require_GET
@requer_token_mcp
def list_operadores(request):
    qs = Operador.objects.select_related('pa', 'pa__ilha', 'pa__ilha__setor').order_by('name')
    q = (request.GET.get('q') or '').strip()
    if q:
        filtro = (
            Q(name__icontains=q)
            | Q(pa__name__icontains=q)
            | Q(pa__ilha__name__icontains=q)
            | Q(pa__ilha__setor__name__icontains=q)
        )
        if q.isdigit():
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro)
    limit = parse_limit(request)
    itens = [_serialize_operador(o) for o in qs[:limit]]
    return JsonResponse({'count': len(itens), 'results': itens})


@require_GET
@requer_token_mcp
def get_operador(request, pk):
    op = get_object_or_404(
        Operador.objects.select_related('pa', 'pa__ilha', 'pa__ilha__setor'),
        pk=pk,
    )
    data = _serialize_operador(op)
    was = (
        WhatsAppAccount.objects.filter(operador=op)
        .select_related('chip', 'operador')
        .order_by('-updated_at')
    )
    data['whatsapp_accounts'] = [_serialize_whatsapp(w) for w in was]
    return JsonResponse(data)


@require_GET
@requer_token_mcp
def list_whatsapp(request):
    qs = (
        WhatsAppAccount.objects.select_related('operador', 'chip')
        .order_by('-updated_at')
    )
    status = (request.GET.get('status') or '').strip()
    if status:
        qs = qs.filter(status=status)

    q = (request.GET.get('q') or '').strip()
    if q:
        filtro = (
            Q(phone_number__icontains=q)
            | Q(operador__name__icontains=q)
            | Q(chip__line_number__icontains=q)
        )
        if q.isdigit():
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro)

    limit = parse_limit(request)
    itens = [_serialize_whatsapp(w) for w in qs[:limit]]
    return JsonResponse({'count': len(itens), 'results': itens})


@require_GET
@requer_token_mcp
def get_whatsapp(request, pk):
    wa = get_object_or_404(
        WhatsAppAccount.objects.select_related('operador', 'chip'),
        pk=pk,
    )
    return JsonResponse(_serialize_whatsapp(wa))
