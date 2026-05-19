from django.urls import path
from . import views

app_name = 'equipment'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('create/', views.EquipmentCreateView.as_view(), name='equipment_create'),
    path('<int:pk>/update/', views.EquipmentUpdateView.as_view(), name='equipment_update'),
]
