"""URLs da API externa v1 (auth + recursos por app)."""

from django.urls import path

from discador import api_views as discador_api
from integracoes import api_auth

urlpatterns = [
    path('auth/', api_auth.auth, name='api_v1_auth'),
    path('discador/ramais/', discador_api.get_ramais, name='api_v1_discador_ramais'),
]
