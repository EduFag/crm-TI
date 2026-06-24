"""Flags de permissão do helpdesk disponíveis em todos os templates."""
from helpdesk.ticket_access import (
    usuario_eh_operador_helpdesk,
    usuario_pode_acessar_dashboard_e_historico,
    usuario_pode_operar_kanban,
)


def helpdesk_permissoes(request):
    user = request.user
    if not user.is_authenticated:
        return {}
    return {
        'pode_operar_kanban': usuario_pode_operar_kanban(user),
        'pode_acessar_dashboard_helpdesk': usuario_pode_acessar_dashboard_e_historico(user),
        'eh_operador_helpdesk': usuario_eh_operador_helpdesk(user),
    }
