from django.urls import path
from . import views

urlpatterns = [
    path('complejos/', views.lista_complejos, name='lista_complejos'),
    path('complejos/crear/', views.crear_complejo, name='crear_complejo'),
    path('complejos/<int:complejo_id>/', views.detalle_complejo, name='detalle_complejo'),
    path('propiedades/<int:propiedad_id>/', views.detalle_propiedad, name='detalle_propiedad'),
    path('propiedades/<int:propiedad_id>/editar/', views.editar_propiedad, name='editar_propiedad'),
    path('complejos/<int:complejo_id>/editar/', views.editar_complejo, name='editar_complejo'),
    path('complejos/<int:complejo_id>/añadir-propiedad/', views.crear_propiedad, name='crear_propiedad'),
    path('complejos/<int:complejo_id>/añadir-multiples-propiedades/', views.crear_propiedades_multiples, name='crear_propiedades_multiples'),
    path('propiedades/<int:propiedad_id>/asignar-contrato/', views.asignar_contrato, name='asignar_contrato'),
]
