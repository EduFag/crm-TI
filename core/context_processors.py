from core.permissions import modulos_permitidos_para_usuario


def modulos_menu(request):
    """Módulos permitidos e estado do menu lateral (ativo/expandido por rota)."""
    path = getattr(request, 'path', '') or ''
    return {
        'modulos_permitidos': modulos_permitidos_para_usuario(request.user),
        'menu_inicio_ativo': path == '/',
        'menu_helpdesk_ativo': path.startswith('/helpdesk/'),
        'menu_chips_ativo': path.startswith('/chips/'),
        'menu_emails_ativo': path.startswith('/emails/'),
        'menu_equipment_ativo': path.startswith('/equipment/'),
        'menu_discador_ativo': path.startswith('/discador/'),
        'menu_usuarios_ativo': path.startswith('/usuarios/'),
        'menu_equipes_ativo': path.startswith('/equipes/'),
        'menu_auditoria_ativo': path.startswith('/auditoria/'),
        'menu_integracoes_ia_ativo': path.startswith('/integracoes/'),
        'menu_suporte_expandido': path.startswith('/helpdesk/'),
        'menu_gestao_expandida': any(
            path.startswith(prefixo)
            for prefixo in ('/chips/', '/emails/', '/equipment/', '/discador/')
        ),
        'menu_admin_expandida': any(
            path.startswith(prefixo)
            for prefixo in ('/usuarios/', '/equipes/', '/auditoria/')
        ),
        'menu_integracoes_expandida': path.startswith('/integracoes/'),
    }
