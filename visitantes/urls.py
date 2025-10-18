from django.urls import path
from . import views

urlpatterns = [
    path('visitantes/', views.lista_visitantes, name='lista_visitantes'),
    path('visitantes/registrar/', views.registrar_visitante, name='registrar_visitante'),
    path('visitantes/historial/', views.historial_visitantes, name='historial_visitantes'),
]