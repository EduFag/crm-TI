from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = 'chips'

urlpatterns = [
    # Página única com abas
    path('', views.ChipsView.as_view(), name='dashboard'),
    path('assign/', views.ChipsAssignmentPostView.as_view(), name='assignment'),

    # API Grid Tabulator
    path('api/grid/', views.ChipGridDataView.as_view(), name='grid_data'),
    path('api/grid/create/', views.ChipGridCreateView.as_view(), name='grid_create'),
    path('api/grid/create/modal/', views.ChipGridCreateModalView.as_view(), name='grid_create_modal'),
    path('api/grid/<int:pk>/', views.ChipGridUpdateView.as_view(), name='grid_update'),
    path('api/grid/<int:pk>/transfer/', views.ChipTransferView.as_view(), name='grid_transfer'),
    path('api/grid/<int:pk>/return/', views.ChipReturnView.as_view(), name='grid_return'),
    path('api/grid/<int:pk>/transfer/modal/', views.ChipTransferModalView.as_view(), name='grid_transfer_modal'),
    path('api/grid/<int:pk>/toggle-email/', views.ChipToggleEmailView.as_view(), name='chip_toggle_email'),
    path('api/grid/<int:pk>/observation/', views.ChipObservationModalView.as_view(), name='chip_observation_modal'),

    # Modais HTMX (create/update)
    path('operators/create/', views.OperatorCreateView.as_view(), name='operator_create'),
    path('operators/<int:pk>/edit/', views.OperatorUpdateView.as_view(), name='operator_edit'),
    path('batches/create/', views.BatchCreateView.as_view(), name='batch_create'),
    path('batches/<int:pk>/edit/', views.BatchUpdateView.as_view(), name='batch_edit'),
    path('batches/<int:pk>/delete/', views.batch_delete_view, name='batch_delete'),
    path('management/create/', views.ChipCreateView.as_view(), name='chip_create'),
    path('management/<int:pk>/edit/', views.ChipUpdateView.as_view(), name='chip_edit'),
    path('return/<int:pk>/', views.ReturnChipView.as_view(), name='return_chip'),
    path('recharge/new/', views.RechargeCreateView.as_view(), name='recharge_create'),
    path('transfer/', views.ChipGeneralTransferView.as_view(), name='general_transfer'),

    # Rotas legadas → redirecionam para aba correspondente
    path('operators/', RedirectView.as_view(url='/chips/?tab=operators', permanent=False), name='operator_list'),
    path('batches/', RedirectView.as_view(url='/chips/?tab=envelopes', permanent=False), name='batch_list'),
    path('management/', RedirectView.as_view(url='/chips/?tab=chips', permanent=False), name='chip_list'),
]
