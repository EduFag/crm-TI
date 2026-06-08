"""Utilitários de filtro de período para o dashboard de chips."""

from datetime import date, timedelta

from django.utils import timezone


def periodo_padrao():
    """Retorna (date_from, date_to) do mês atual até hoje."""
    hoje = timezone.localdate()
    inicio = hoje.replace(day=1)
    return inicio, hoje


def periodo_mes_anterior():
    """Retorna (date_from, date_to) do mês anterior completo."""
    hoje = timezone.localdate()
    primeiro_mes_atual = hoje.replace(day=1)
    ultimo_mes_anterior = primeiro_mes_atual - timedelta(days=1)
    inicio = ultimo_mes_anterior.replace(day=1)
    return inicio, ultimo_mes_anterior


def resolver_periodo(request):
    """Lê date_from/date_to do GET ou aplica default do mês atual."""
    padrao_inicio, padrao_fim = periodo_padrao()
    date_from = _parse_date(request.GET.get('date_from')) or padrao_inicio
    date_to = _parse_date(request.GET.get('date_to')) or padrao_fim
    if date_from > date_to:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _parse_date(valor):
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None
