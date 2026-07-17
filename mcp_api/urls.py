from django.urls import path

from mcp_api.views import audit, chips, emails, equipment, helpdesk, users

urlpatterns = [
    # Helpdesk
    path('tickets/', helpdesk.list_tickets, name='mcp_list_tickets'),
    path('tickets/<int:pk>/', helpdesk.get_ticket, name='mcp_get_ticket'),
    path('tickets/<int:pk>/comments/', helpdesk.list_ticket_comments, name='mcp_list_ticket_comments'),
    path('tickets/<int:pk>/assistente/comentarios/', helpdesk.post_assistente_comentario, name='mcp_assistente_comentario'),
    path('tickets/<int:pk>/priority/', helpdesk.post_ticket_priority, name='mcp_ticket_priority'),
    path('tickets/<int:pk>/status/', helpdesk.post_ticket_status, name='mcp_ticket_status'),
    path('tickets/<int:pk>/assistente/escalar/', helpdesk.post_assistente_escalar, name='mcp_assistente_escalar'),

    # Chips
    path('chips/', chips.list_chips, name='mcp_list_chips'),
    path('chips/by-line/<str:line_number>/', chips.lookup_chip_by_line, name='mcp_lookup_chip_by_line'),
    path('chips/<int:pk>/', chips.get_chip, name='mcp_get_chip'),
    path('chips/<int:pk>/movements/', chips.list_chip_movements, name='mcp_list_chip_movements'),

    # Equipment
    path('equipment/', equipment.list_equipment, name='mcp_list_equipment'),
    path('equipment/by-tag/<str:tag>/', equipment.lookup_equipment_by_tag, name='mcp_lookup_equipment_by_tag'),
    path('equipment/<int:pk>/', equipment.get_equipment, name='mcp_get_equipment'),
    path('equipment/<int:pk>/logs/', equipment.list_equipment_logs, name='mcp_list_equipment_logs'),

    # Emails
    path('domains/', emails.list_domains, name='mcp_list_domains'),
    path('accounts/', emails.list_accounts, name='mcp_list_accounts'),
    path('accounts/<int:pk>/', emails.get_account, name='mcp_get_account'),

    # Users
    path('users/', users.list_users, name='mcp_list_users'),
    path('users/by-username/<str:username>/', users.lookup_user_by_username, name='mcp_lookup_user_by_username'),
    path('users/<int:pk>/', users.get_user, name='mcp_get_user'),
    path('equipes/', users.list_equipes, name='mcp_list_equipes'),
    path('equipes/<int:pk>/membros/', users.list_equipe_membros, name='mcp_list_equipe_membros'),

    # Audit / sistema
    path('acoes/', audit.list_acoes, name='mcp_list_acoes'),
    path('acoes/<int:pk>/', audit.get_acao, name='mcp_get_acao'),
    path('sistema/status/', audit.sistema_status, name='mcp_sistema_status'),
]
