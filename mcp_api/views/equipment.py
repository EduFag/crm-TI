from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from equipment.models import Equipment, EquipmentLog
from mcp_api.auth import requer_token_mcp
from mcp_api.serializers import parse_limit, serialize_equipment, serialize_equipment_log


@require_GET
@requer_token_mcp
def list_equipment(request):
    qs = Equipment.objects.all().order_by('-updated_at')

    status = (request.GET.get('status') or '').strip()
    if status:
        qs = qs.filter(status=status)

    eq_type = (request.GET.get('type') or '').strip()
    if eq_type:
        qs = qs.filter(type=eq_type)

    q = (request.GET.get('q') or '').strip()
    if q:
        filtro = (
            Q(tag__icontains=q)
            | Q(serial_number__icontains=q)
            | Q(brand_model__icontains=q)
            | Q(current_employee__icontains=q)
        )
        if q.isdigit():
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro)

    limit = parse_limit(request)
    itens = [serialize_equipment(e) for e in qs[:limit]]
    return JsonResponse({'count': len(itens), 'results': itens})


@require_GET
@requer_token_mcp
def get_equipment(request, pk):
    eq = get_object_or_404(Equipment, pk=pk)
    return JsonResponse(serialize_equipment(eq))


@require_GET
@requer_token_mcp
def lookup_equipment_by_tag(request, tag):
    eq = Equipment.objects.filter(tag__iexact=tag).first()
    if not eq:
        return JsonResponse({'error': 'Equipamento não encontrado.'}, status=404)
    return JsonResponse(serialize_equipment(eq))


@require_GET
@requer_token_mcp
def list_equipment_logs(request, pk):
    eq = get_object_or_404(Equipment, pk=pk)
    qs = EquipmentLog.objects.filter(equipment=eq).order_by('-timestamp')
    limit = parse_limit(request)
    itens = [serialize_equipment_log(log) for log in qs[:limit]]
    return JsonResponse({'equipment_id': eq.pk, 'count': len(itens), 'results': itens})
