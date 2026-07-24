"""Flags de permissão e versão de assets do helpdesk nos templates."""
from django.conf import settings

from helpdesk.ticket_access import (
    usuario_eh_operador_helpdesk,
    usuario_pode_acessar_dashboard_e_historico,
    usuario_pode_gerenciar_comentarios,
    usuario_pode_operar_kanban,
)


def helpdesk_permissoes(request):
    user = request.user
    asset_v = getattr(settings, 'HELPDESK_FRONTEND_VERSION', '1')
    base = {
        # Usado em ?v= nos statics e nas URLs HTMX do helpdesk
        'helpdesk_asset_v': asset_v,
    }
    if not user.is_authenticated:
        return base
    return {
        **base,
        'pode_operar_kanban': usuario_pode_operar_kanban(user),
        'pode_acessar_dashboard_helpdesk': usuario_pode_acessar_dashboard_e_historico(user),
        'eh_operador_helpdesk': usuario_eh_operador_helpdesk(user),
        'pode_gerenciar_comentarios': usuario_pode_gerenciar_comentarios(user),
    }
