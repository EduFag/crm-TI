from django.urls import path

from integracoes import views

app_name = 'integracoes'

urlpatterns = [
    path('ia/', views.IAListView.as_view(), name='ia_list'),
    path('ia/aprendizado/', views.ia_aprendizado, name='ia_aprendizado'),
    path('ia/aprendizado/toggle/', views.ia_aprendizado_toggle, name='ia_aprendizado_toggle'),
    path('ia/aprendizado/gerar/', views.ia_aprendizado_gerar, name='ia_aprendizado_gerar'),
    path('ia/aprendizado/embeddings/', views.ia_embeddings_recalcular, name='ia_embeddings_recalcular'),
    path('ia/aprendizado/interacoes/<int:pk>/nota/', views.ia_interacao_nota, name='ia_interacao_nota'),
    path('ia/aprendizado/chunks/novo/', views.ia_chunk_create, name='ia_chunk_create'),
    path('ia/aprendizado/chunks/<int:pk>/editar/', views.ia_chunk_update, name='ia_chunk_update'),
    path('ia/aprendizado/chunks/<int:pk>/toggle/', views.ia_chunk_toggle_ativo, name='ia_chunk_toggle'),
    path('ia/aprendizado/chunks/<int:pk>/excluir/', views.ia_chunk_delete, name='ia_chunk_delete'),
    path('ia/aprendizado/chat/', views.ia_aprendizado_chat, name='ia_aprendizado_chat'),
    path('ia/aprendizado/chat/limpar/', views.ia_aprendizado_chat_limpar, name='ia_aprendizado_chat_limpar'),
    path('ia/aprendizado/conversas/', views.ia_aprendizado_conversas, name='ia_aprendizado_conversas'),
    path('ia/aprendizado/conversas/nova/', views.ia_aprendizado_conversa_nova, name='ia_aprendizado_conversa_nova'),
    path('ia/aprendizado/conversas/<int:pk>/', views.ia_aprendizado_conversa_get, name='ia_aprendizado_conversa_get'),
    path('ia/nova/', views.IAWizardCreateView.as_view(), name='ia_create'),
    path('ia/<int:pk>/editar/', views.IAUpdateView.as_view(), name='ia_update'),
    path('ia/<int:pk>/toggle/', views.ia_toggle_active, name='ia_toggle'),
    path('ia/<int:pk>/excluir/', views.ia_delete, name='ia_delete'),
    # APIs externas (MoneyConsig, etc.)
    path('api/', views.ApiListView.as_view(), name='api_list'),
    path('api/nova/', views.ApiWizardCreateView.as_view(), name='api_create'),
    path('api/<int:pk>/editar/', views.ApiUpdateView.as_view(), name='api_update'),
    path('api/<int:pk>/toggle/', views.api_toggle_active, name='api_toggle'),
    path('api/<int:pk>/excluir/', views.api_delete, name='api_delete'),
    path('api/<int:pk>/testar/', views.api_testar, name='api_testar'),
    # Tokens de API externa (CRM-TI → sistemas do cliente)
    path('tokens/', views.TokenListView.as_view(), name='tokens_list'),
    path('tokens/gerar/', views.TokenGerarView.as_view(), name='tokens_gerar'),
    path('tokens/<int:pk>/revogar/', views.token_revogar, name='tokens_revogar'),
]
