from django.urls import path
from . import views

urlpatterns = [
    path('comunidades/', views.lista_comunidades, name='lista_comunidades'),
    path('comunidades/crear/', views.crear_comunidad, name='crear_comunidad'),
    path('comunidades/<int:comunidad_id>/', views.detalle_comunidad, name='detalle_comunidad'),
    path('comunidades/<int:comunidad_id>/añadir-propiedad/', views.crear_propiedad, name='crear_propiedad'),
]
