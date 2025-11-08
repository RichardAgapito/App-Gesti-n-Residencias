from django.urls import path
from .views import ListaAvisos, DetalleAviso, CrearAviso

app_name = 'avisos'

urlpatterns = [
    path('', ListaAvisos.as_view(), name='lista_avisos'),
    path('crear/', CrearAviso.as_view(), name='crear_aviso'),
    path('<int:pk>/', DetalleAviso.as_view(), name='detalle_aviso'),
]