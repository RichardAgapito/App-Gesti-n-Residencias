from django.urls import path
from . import views

urlpatterns = [
    path('complejos/', views.lista_complejos, name='lista_complejos'),
    path('complejos/crear/', views.crear_complejo, name='crear_complejo'),
    path('complejos/<int:complejo_id>/', views.detalle_complejo, name='detalle_complejo'),
    path('complejos/<int:complejo_id>/añadir-propiedad/', views.crear_propiedad, name='crear_propiedad'),
]
