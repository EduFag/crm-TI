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
    
    # Gerenciamento de Categorias
    path('categories/', views.CategoriesManageView.as_view(), name='categories'),
    path('categories/create/<str:model_type>/', views.category_create_action, name='category_create_action'),
    path('categories/toggle/<str:model_type>/<int:pk>/', views.category_toggle_active, name='category_toggle_active'),
    
    # Real-Time e Partials via HTMX
    path('poll/', views.poll_ticket_updates, name='poll'),
    path('kanban/board/', views.KanbanBoardPartialView.as_view(), name='kanban_board'),
    path('dashboard/metrics/', views.DashboardMetricsPartialView.as_view(), name='dashboard_metrics'),
    
    # Criação de chamados
    path('ticket/create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('category/create/', views.ticket_category_create, name='category_create'),
    
    # Ações assíncronas via Fetch/HTMX
    path('ticket/<int:pk>/update-status/', views.ticket_update_status, name='ticket_update_status'),
    path('ticket/<int:pk>/finalize/', views.ticket_finalize, name='ticket_finalize'),
    path('ticket/<int:pk>/drawer/', views.ticket_drawer, name='ticket_drawer'),
    path('ticket/<int:pk>/edit/', views.ticket_edit, name='ticket_edit'),
    path('ticket/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('ticket/<int:pk>/attachments/', views.ticket_attachments, name='ticket_attachments'),
    path('ticket/<int:pk>/transfer/', views.ticket_transfer, name='ticket_transfer'),
    path('ticket/<int:pk>/comment/', views.ticket_add_comment, name='ticket_add_comment'),
]
