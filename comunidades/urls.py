# comunidades/urls.py (archivo nuevo)
from django.urls import path
from . import views

urlpatterns = [
    # 1. Página para ver la LISTA de todas las comunidades
    path('comunidades/', views.lista_comunidades, name='lista_comunidades'),

    # 2. Página con el formulario para CREAR una nueva comunidad
    path('comunidades/crear/', views.crear_comunidad, name='crear_comunidad'),

    # 3. Página para ver el DETALLE de UNA comunidad específica
    #    El <int:comunidad_id> es una parte variable que contendrá el ID de la comunidad
    path('comunidades/<int:comunidad_id>/', views.detalle_comunidad, name='detalle_comunidad'),

    # 4. Página para AÑADIR una propiedad a una comunidad específica
    path('comunidades/<int:comunidad_id>/añadir-propiedad/', views.crear_propiedad, name='crear_propiedad'),
]