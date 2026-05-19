from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_view(request):
    """
    Tela inicial da aplicação.
    Exibe o painel de controle (dashboard) apenas para usuários autenticados.
    """
    return render(request, 'core/dashboard.html')
