from django.urls import path
from . import views

app_name = 'emails'

urlpatterns = [
    # Dashboard Unificado
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('create/', views.EmailAccountCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/reset/', views.ResetPasswordView.as_view(), name='account_reset_password'),
    path('accounts/<int:pk>/toggle-status/', views.ToggleAccountStatusView.as_view(), name='account_toggle_status'),

    # Gestão de Domínios
    path('domains/', views.EmailDomainListView.as_view(), name='domain_list'),
    path('domains/create/', views.EmailDomainCreateView.as_view(), name='domain_create'),
]
