from django.urls import path

from integracoes import views

app_name = 'integracoes'

urlpatterns = [
    path('ia/', views.IAListView.as_view(), name='ia_list'),
    path('ia/aprendizado/', views.ia_aprendizado, name='ia_aprendizado'),
    path('ia/aprendizado/toggle/', views.ia_aprendizado_toggle, name='ia_aprendizado_toggle'),
    path('ia/aprendizado/gerar/', views.ia_aprendizado_gerar, name='ia_aprendizado_gerar'),
    path('ia/aprendizado/chunks/novo/', views.ia_chunk_create, name='ia_chunk_create'),
    path('ia/aprendizado/chunks/<int:pk>/editar/', views.ia_chunk_update, name='ia_chunk_update'),
    path('ia/aprendizado/chunks/<int:pk>/excluir/', views.ia_chunk_delete, name='ia_chunk_delete'),
    path('ia/nova/', views.IAWizardCreateView.as_view(), name='ia_create'),
    path('ia/<int:pk>/editar/', views.IAUpdateView.as_view(), name='ia_update'),
    path('ia/<int:pk>/toggle/', views.ia_toggle_active, name='ia_toggle'),
    path('ia/<int:pk>/excluir/', views.ia_delete, name='ia_delete'),
]
