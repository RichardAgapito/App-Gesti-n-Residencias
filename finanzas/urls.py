from django.urls import path
from .views import (
    PlanCuotaListView,
    PlanCuotaCreateView,
    PlanCuotaUpdateView,
    ConceptoCobroListView,
    ConceptoCobroCreateView,
    ConceptoCobroUpdateView,
    MetodoPagoListView,
    MetodoPagoCreateView,
    MetodoPagoUpdateView,
    FacturaListView,
    FacturaCreateView,
    FacturaUpdateView,
    FacturaDetailView, # Added
    MisFacturasView,
    RecaudoCreateView,
    ReporteCobranzaView,
    GenerateInvoicesView, # Added
    ReciboPagoView, # Added
    get_conceptos_plan,
    UpdateFinancialStatusView, # Added
    ConfiguracionFinancieraUpdateView,
    SeleccionarComplejoFinanzasView, # Added
    SeleccionarComplejoFinanzasView, # Added
    get_conceptos_contrato, # Added
    RegistrarPagoResidenteView, # Added
    FacturaDetalleResidenteView # Added
)

urlpatterns = [
    # URLs para Admin
    path('planes/', PlanCuotaListView.as_view(), name='lista_planes_cuota'),
    path('planes/crear/', PlanCuotaCreateView.as_view(), name='crear_plan_cuota'),
    path('planes/<int:pk>/editar/', PlanCuotaUpdateView.as_view(), name='editar_plan_cuota'),

    path('conceptos/', ConceptoCobroListView.as_view(), name='lista_conceptos_cobro'),
    path('conceptos/crear/', ConceptoCobroCreateView.as_view(), name='crear_concepto_cobro'),
    path('conceptos/<int:pk>/editar/', ConceptoCobroUpdateView.as_view(), name='editar_concepto_cobro'),

    path('metodos-pago/', MetodoPagoListView.as_view(), name='lista_metodos_pago'),
    path('metodos-pago/crear/', MetodoPagoCreateView.as_view(), name='crear_metodo_pago'),
    path('metodos-pago/<int:pk>/editar/', MetodoPagoUpdateView.as_view(), name='editar_metodo_pago'),

    # URLs para Gerente
    path('facturas/', FacturaListView.as_view(), name='lista_facturas'),
    path('facturas/crear/', FacturaCreateView.as_view(), name='crear_factura'),
    path('facturas/<int:pk>/', FacturaDetailView.as_view(), name='detalle_factura'), # Added
    path('facturas/<int:pk>/editar/', FacturaUpdateView.as_view(), name='editar_factura'),
    path('facturas/<int:factura_pk>/registrar-pago/', RecaudoCreateView.as_view(), name='registrar_pago'),
    path('reporte-cobranza/', ReporteCobranzaView.as_view(), name='reporte_cobranza'),
    path('facturas/generar-automatico/', GenerateInvoicesView.as_view(), name='generar_facturas_automatico'), # Added
    path('recibo/<int:pk>/', ReciboPagoView.as_view(), name='ver_recibo'), # Added
    path('ajax/get-conceptos-plan/', get_conceptos_plan, name='get_conceptos_plan'), # Added
    path('configuracion/', ConfiguracionFinancieraUpdateView.as_view(), name='configuracion_financiera'),
    path('configuracion/seleccionar/', SeleccionarComplejoFinanzasView.as_view(), name='seleccionar_complejo_finanzas'),

    # URLs para Residente
    path('mis-facturas/', MisFacturasView.as_view(), name='mis_facturas'),
    
    path('facturas/generar-automatico/', GenerateInvoicesView.as_view(), name='generar_facturas_automatico'),
    
    # NUEVA RUTA:
    path('facturas/actualizar-estados/', UpdateFinancialStatusView.as_view(), name='actualizar_estados_financieros'),
    path('ajax/get-conceptos-contrato/', get_conceptos_contrato, name='get_conceptos_contrato'), # Helper para crear factura
    path('facturas/<int:pk>/pagar/', RegistrarPagoResidenteView.as_view(), name='registrar_pago_residente'),
    path('facturas/<int:pk>/detalle-residente/', FacturaDetalleResidenteView.as_view(), name='detalle_factura_residente'),
]
