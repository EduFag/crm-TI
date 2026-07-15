"""
URL configuration for setup project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('helpdesk/', include('helpdesk.urls')),
    path('chips/', include('chips.urls')),
    path('emails/', include('emails.urls')),
    path('equipment/', include('equipment.urls')),
    path('discador/', include('discador.urls')),
    path('integracoes/', include('integracoes.urls')),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Páginas de erro customizadas (exibidas quando DEBUG=False)
handler404 = 'core.views.pagina_nao_encontrada'
handler500 = 'core.views.erro_servidor'
handler403 = 'core.views.acesso_negado'
