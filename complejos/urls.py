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
    path('api/residentes/', views.get_residentes_json, name='get_residentes_json'),
    path('propiedades/<int:propiedad_id>/cancelar-contrato/<int:propiedad_persona_id>/', views.cancelar_contrato, name='cancelar_contrato'),

    # URLs para el sistema de reservas
    path('reservas/', views.crear_reserva_view, name='crear_reserva'),
    path('mis-reservas/', views.mis_reservas_view, name='mis_reservas'),
    path('admin/reservas/', views.admin_reservas_view, name='admin_reservas'),
    path('admin/reservas/<int:reserva_id>/cancelar/', views.cancelar_reserva_view, name='cancelar_reserva'),
    path('admin_dashboard/amenidades/', views.gestionar_amenidades_view, name='gestionar_amenidades'),
    path('admin_dashboard/amenidades/<int:amenidad_id>/editar/', views.editar_amenidad_view, name='editar_amenidad'),
    path('admin_dashboard/amenidades/<int:amenidad_id>/eliminar/', views.eliminar_amenidad_view, name='eliminar_amenidad'),
]