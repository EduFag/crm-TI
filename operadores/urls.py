from django.urls import path
from .views import (
    DashboardView,
    PABatchCreateView,
    OperadorCreateView,
    OperadorUpdateView,
    OperadorDeleteView,
    WhatsAppAccountCreateView,
    WhatsAppAccountUpdateView,
    PACreateView,
    PAUpdateView,
    PADeleteView,
    IlhaUpdateView,
    AlocarOperadorView,
    OperadorWhatsAppManageView,
    WhatsAppAccountChangeStatusView,
    OperadorProfileModalView,
)

app_name = 'operadores'

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('pas/batch/', PABatchCreateView.as_view(), name='pa_batch_create'),
    path('pas/create/', PACreateView.as_view(), name='pa_create'),
    path('pas/<int:pk>/edit/', PAUpdateView.as_view(), name='pa_edit'),
    path('pas/<int:pk>/delete/', PADeleteView.as_view(), name='pa_delete'),
    path('ilhas/<int:pk>/edit/', IlhaUpdateView.as_view(), name='ilha_edit'),
    path('pas/<int:pa_id>/alocar/', AlocarOperadorView.as_view(), name='pa_alocar_operador'),
    path('funcionarios/create/', OperadorCreateView.as_view(), name='operador_create'),
    path('funcionarios/<int:pk>/edit/', OperadorUpdateView.as_view(), name='operador_edit'),
    path('funcionarios/<int:pk>/delete/', OperadorDeleteView.as_view(), name='operador_delete'),
    path('funcionarios/<int:pk>/profile/', OperadorProfileModalView.as_view(), name='operador_profile'),
    path('funcionarios/<int:operador_id>/whatsapp/manage/', OperadorWhatsAppManageView.as_view(), name='operador_whatsapp_manage'),
    path('whatsapp/create/', WhatsAppAccountCreateView.as_view(), name='whatsapp_create'),
    path('whatsapp/<int:pk>/edit/', WhatsAppAccountUpdateView.as_view(), name='whatsapp_edit'),
    path('whatsapp/<int:pk>/change-status/', WhatsAppAccountChangeStatusView.as_view(), name='whatsapp_change_status'),
]
