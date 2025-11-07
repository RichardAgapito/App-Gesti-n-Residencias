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
    path('visitas/<int:visita_id>/editar/', views.editar_visita_view, name='editar_visita'),
    path('visitas/<int:visita_id>/eliminar/', views.eliminar_visita_view, name='eliminar_visita'),
    path('preautorizaciones/', views.lista_preautorizaciones_view, name='lista_preautorizaciones'),
    path('preautorizaciones/crear/', views.crear_preautorizacion_view, name='crear_preautorizacion'),
    path('preautorizaciones/<int:preautorizacion_id>/', views.detalle_preautorizacion_view, name='detalle_preautorizacion'),
    path('preautorizaciones/<int:preautorizacion_id>/editar/', views.editar_preautorizacion_view, name='editar_preautorizacion'),
    path('preautorizaciones/<int:preautorizacion_id>/eliminar/', views.eliminar_preautorizacion_view, name='eliminar_preautorizacion'),
]
