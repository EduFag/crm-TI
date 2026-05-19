from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

urlpatterns = [
    # Dashboard (Tela inicial) - Acessível apenas para logados via decorator
    path('', views.dashboard_view, name='dashboard'),
    
    # URL /login/ (Tela de login) - Redireciona para / se já estiver logado
    path('login/', LoginView.as_view(
        template_name='core/login.html',
        redirect_authenticated_user=True
    ), name='login'),
    
    # URL /logout/
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]
