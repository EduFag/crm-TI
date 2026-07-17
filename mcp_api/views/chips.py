from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from chips.models import Chip, ChipMovement
from mcp_api.auth import requer_token_mcp
from mcp_api.serializers import parse_limit, serialize_chip, serialize_chip_movement


@require_GET
@requer_token_mcp
def list_chips(request):
    qs = Chip.objects.select_related('operator', 'batch').order_by('-updated_at')

    status = (request.GET.get('status') or '').strip()
    if status:
        qs = qs.filter(status=status)

    usage = (request.GET.get('usage_status') or '').strip()
    if usage:
        qs = qs.filter(usage_status=usage)

    active = (request.GET.get('active') or '').strip().lower()
    if active in ('1', 'true'):
        qs = qs.filter(is_active=True)
    elif active in ('0', 'false'):
        qs = qs.filter(is_active=False)

    q = (request.GET.get('q') or '').strip()
    if q:
        filtro = Q(line_number__icontains=q) | Q(iccid__icontains=q) | Q(observacao__icontains=q)
        if q.isdigit():
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro)

    limit = parse_limit(request)
    itens = [serialize_chip(c) for c in qs[:limit]]
    return JsonResponse({'count': len(itens), 'results': itens})


@require_GET
@requer_token_mcp
def get_chip(request, pk):
    chip = get_object_or_404(Chip.objects.select_related('operator', 'batch'), pk=pk)
    return JsonResponse(serialize_chip(chip))


@require_GET
@requer_token_mcp
def lookup_chip_by_line(request, line_number):
    digits = ''.join(c for c in line_number if c.isdigit())
    chip = (
        Chip.objects.select_related('operator', 'batch')
        .filter(Q(line_number=line_number) | Q(line_number=digits))
        .first()
    )
    if not chip:
        return JsonResponse({'error': 'Chip não encontrado.'}, status=404)
    return JsonResponse(serialize_chip(chip))


@require_GET
@requer_token_mcp
def list_chip_movements(request, pk):
    chip = get_object_or_404(Chip, pk=pk)
    qs = (
        ChipMovement.objects.filter(chip=chip)
        .select_related('employee_user', 'registered_by')
        .order_by('-timestamp')
    )
    limit = parse_limit(request)
    itens = [serialize_chip_movement(m) for m in qs[:limit]]
    return JsonResponse({'chip_id': chip.pk, 'count': len(itens), 'results': itens})
