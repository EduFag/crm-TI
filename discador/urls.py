from django.urls import path
from . import views

app_name = 'discador'

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
    path('configuracoes/', views.ConfiguracoesAPIView.as_view(), name='configuracoes_api'),
    path('atualizar-blacklist/', views.AtualizarBlacklistView.as_view(), name='atualizar_blacklist'),
    path('regras/', views.RegrasReciclagemView.as_view(), name='regras_reciclagem'),
    path('reciclar-bases/', views.ReciclarBasesView.as_view(), name='reciclar_bases'),
    path('reciclagem-painel/', views.ReciclarBasesView.as_view(), name='recycling_panel'),
    path('blacklist/', views.BlacklistView.as_view(), name='blacklist_ativa'),
    path('consulta-telefone/', views.ConsultaTelefoneView.as_view(), name='consulta_telefone'),
    path('historico-importacoes/', views.HistoricoImportacoesView.as_view(), name='historico_importacoes'),
    path('historico-processamentos/', views.HistoricoProcessamentosView.as_view(), name='historico_processamentos'),
]
