from django.urls import path

from integracoes import views

app_name = 'integracoes'

urlpatterns = [
    path('ia/', views.IAListView.as_view(), name='ia_list'),
    path('ia/aprendizado/', views.ia_aprendizado, name='ia_aprendizado'),
    path('ia/aprendizado/toggle/', views.ia_aprendizado_toggle, name='ia_aprendizado_toggle'),
    path('ia/aprendizado/gerar/', views.ia_aprendizado_gerar, name='ia_aprendizado_gerar'),
    path('ia/nova/', views.IAWizardCreateView.as_view(), name='ia_create'),
    path('ia/<int:pk>/editar/', views.IAUpdateView.as_view(), name='ia_update'),
    path('ia/<int:pk>/toggle/', views.ia_toggle_active, name='ia_toggle'),
    path('ia/<int:pk>/excluir/', views.ia_delete, name='ia_delete'),
]
