from django.urls import path
from . import views

app_name = 'helpdesk'

urlpatterns = [
    # Dashboard de Métricas
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    
    # Kanban principal (Vamos redirecionar a home do helpdesk para o dashboard ou Kanban, escolhi Kanban como raiz inicial)
    path('', views.KanbanView.as_view(), name='kanban'),
    
    # Histórico e Filtros
    path('history/', views.HistoryListView.as_view(), name='history'),
    
    # Real-Time e Partials via HTMX
    path('poll/', views.poll_ticket_updates, name='poll'),
    path('kanban/board/', views.KanbanBoardPartialView.as_view(), name='kanban_board'),
    path('dashboard/metrics/', views.DashboardMetricsPartialView.as_view(), name='dashboard_metrics'),
    
    # Criação de chamados
    path('ticket/create/', views.TicketCreateView.as_view(), name='ticket_create'),
    
    # Ações assíncronas via Fetch/HTMX
    path('ticket/<int:pk>/update-status/', views.ticket_update_status, name='ticket_update_status'),
    path('ticket/<int:pk>/drawer/', views.ticket_drawer, name='ticket_drawer'),
    path('ticket/<int:pk>/comment/', views.ticket_add_comment, name='ticket_add_comment'),
]
