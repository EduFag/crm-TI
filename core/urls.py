from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', LoginView.as_view(
        template_name='core/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('sem-permissao/', views.sem_permissao_view, name='sem_permissao'),

    # Gestão de usuários (somente ADMIN)
    path('usuarios/', views.UserListView.as_view(), name='user_list'),
    path('usuarios/criar/', views.UserCreateView.as_view(), name='user_create'),
    path('usuarios/<int:pk>/editar/', views.UserUpdateView.as_view(), name='user_update'),
    path('usuarios/<int:pk>/desativar/', views.user_toggle_active, name='user_toggle_active'),

    # Gestão de equipes (somente ADMIN)
    path('equipes/', views.EquipeListView.as_view(), name='equipe_list'),
    path('equipes/criar/', views.EquipeCreateView.as_view(), name='equipe_create'),
    path('equipes/<int:pk>/editar/', views.EquipeUpdateView.as_view(), name='equipe_update'),
    path('equipes/<int:pk>/desativar/', views.equipe_toggle_active, name='equipe_toggle_active'),
]
