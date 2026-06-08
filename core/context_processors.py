from core.permissions import modulos_permitidos_para_usuario


def modulos_menu(request):
    """Disponibiliza os módulos permitidos ao usuário para o menu lateral."""
    return {
        'modulos_permitidos': modulos_permitidos_para_usuario(request.user),
    }
