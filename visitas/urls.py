from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard_visitas'),
    path('visitantes/', views.lista_visitantes_view, name='lista_visitantes'),
    path('visitantes/crear/', views.crear_visitante_view, name='crear_visitante'),
    path('visitantes/<int:visitante_id>/', views.detalle_visitante_view, name='detalle_visitante'),
    path('visitantes/<int:visitante_id>/editar/', views.editar_visitante_view, name='editar_visitante'),
    path('visitantes/<int:visitante_id>/eliminar/', views.eliminar_visitante_view, name='eliminar_visitante'),
    
    path('visitas/', views.lista_visitas_view, name='lista_visitas'),
    path('visitas/crear/', views.crear_visita_view, name='crear_visita'),
    path('visitas/<int:visita_id>/', views.detalle_visita_view, name='detalle_visita'),
    
    # Mantenido de tu rama (guevara_r)
    path('visitas/<int:visita_id>/registrar-salida/', views.registrar_salida_visita_view, name='registrar_salida_visita'),
    
    # Añadido desde la rama principal (residencias_richard)
    path('visitas/<int:visita_id>/editar/', views.editar_visita_view, name='editar_visita'),
    
    # Mantenido de tu rama (guevara_r)
    path('visitas/propiedad/<int:propiedad_id>/residentes/', views.get_residentes_por_propiedad, name='get_residentes_por_propiedad'),
    
    path('preautorizaciones/', views.lista_preautorizaciones_view, name='lista_preautorizaciones'),
    path('preautorizaciones/<int:pa_id>/aprobar/', views.aprobar_preautorizacion_view, name='aprobar_preautorizacion'),
    path('preautorizaciones/<int:pa_id>/cancelar/', views.cancelar_preautorizacion_view, name='cancelar_preautorizacion'),
]
