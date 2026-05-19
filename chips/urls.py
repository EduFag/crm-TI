from django.urls import path
from . import views

app_name = 'chips'

urlpatterns = [
    # Dashboard Principal
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Lotes e Operadoras (Módulo Base)
    path('operators/', views.OperatorListView.as_view(), name='operator_list'),
    path('operators/create/', views.OperatorCreateView.as_view(), name='operator_create'),
    path('batches/', views.BatchListView.as_view(), name='batch_list'),
    path('batches/create/', views.BatchCreateView.as_view(), name='batch_create'),
    
    # Cadastro de Chips
    path('management/', views.ChipListView.as_view(), name='chip_list'),
    path('management/create/', views.ChipCreateView.as_view(), name='chip_create'),
    path('management/<int:pk>/edit/', views.ChipUpdateView.as_view(), name='chip_edit'),
    
    # Fluxo Operacional: Atribuições e Entregas/Devoluções
    path('assign/', views.AssignmentView.as_view(), name='assignment'),
    path('return/<int:pk>/', views.ReturnChipView.as_view(), name='return_chip'),
    
    # Fluxo Financeiro: Recargas
    path('recharge/new/', views.RechargeCreateView.as_view(), name='recharge_create'),
]
