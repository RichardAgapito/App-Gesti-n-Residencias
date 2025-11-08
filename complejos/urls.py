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
    path('contratos/', views.lista_contratos, name='lista_contratos'),

    # URLs para el sistema de reservas
    path('reservas/', views.crear_reserva_view, name='crear_reserva'),
    path('mis-reservas/', views.mis_reservas_view, name='mis_reservas'),
    path('reservas/amenidad/<int:amenidad_id>/disponibilidad/', views.ver_disponibilidad_view, name='ver_disponibilidad'),
    path('admin/reservas/', views.admin_reservas_view, name='admin_reservas'),
    path('admin/reservas/crear/', views.admin_crear_reserva, name='admin_crear_reserva'),
    path('admin/reservas/<int:reserva_id>/editar/', views.admin_editar_reserva, name='admin_editar_reserva'),
    path('admin/reservas/<int:reserva_id>/cancelar/', views.cancelar_reserva_view, name='cancelar_reserva'),
    path('admin/reservas/<int:reserva_id>/approve/', views.approve_reserva, name='approve_reserva'),
    path('admin/reservas/<int:reserva_id>/reject/', views.reject_reserva, name='reject_reserva'),
    path('admin_dashboard/amenidades/', views.gestionar_amenidades_view, name='gestionar_amenidades'),
    path('admin_dashboard/amenidades/<int:amenidad_id>/editar/', views.editar_amenidad_view, name='editar_amenidad'),
    path('admin_dashboard/amenidades/<int:amenidad_id>/eliminar/', views.eliminar_amenidad_view, name='eliminar_amenidad'),
    path('admin_dashboard/amenidades/<int:amenidad_id>/bloquear/', views.bloquear_horario_view, name='bloquear_horario'),
    path('admin_dashboard/amenidades/unblock/<int:reserva_id>/', views.unblock_horario_view, name='unblock_horario'),
    
    # (NUEVO) URLs para Pre-Autorizaciones del Residente
    path('mis-autorizaciones/', views.mis_preautorizaciones_view, name='mis_preautorizaciones'),
    path('mis-autorizaciones/crear/', views.crear_preautorizacion_view, name='crear_preautorizacion'),
    path('mis-autorizaciones/<int:pa_id>/editar/', views.editar_preautorizacion_view, name='editar_preautorizacion'),
    path('mis-autorizaciones/<int:pa_id>/cancelar/', views.cancelar_preautorizacion_view, name='cancelar_preautorizacion'),
]