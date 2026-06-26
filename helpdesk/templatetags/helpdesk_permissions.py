from django import template

from helpdesk.ticket_access import usuario_pode_contestar_chamado

register = template.Library()


@register.simple_tag(takes_context=True)
def pode_contestar_chamado(context, ticket):
    """Indica se o usuário logado pode contestar o chamado."""
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    return usuario_pode_contestar_chamado(request.user, ticket)
