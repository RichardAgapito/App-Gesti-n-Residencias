from django.contrib import admin
from .models import (
    PlanCuota, ConceptoCobro, Factura, DetalleFactura, MetodoPago, Recaudo, 
    PlanConceptoCobro, ConfiguracionFinanciera, ContratoFinanciero, PropiedadPersona, CargoAdicional
)

class PlanConceptoCobroInline(admin.TabularInline):
    model = PlanConceptoCobro
    extra = 1

@admin.register(PlanCuota)
class PlanCuotaAdmin(admin.ModelAdmin):
    inlines = (PlanConceptoCobroInline,)
    list_display = ('nombre', 'complejo', 'frecuencia', 'activo')
    list_filter = ('complejo', 'activo', 'frecuencia')
    search_fields = ('nombre',)

@admin.register(ConceptoCobro)
class ConceptoCobroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'complejo', 'tipo', 'obligatorio')
    list_filter = ('complejo', 'tipo', 'obligatorio')
    search_fields = ('nombre',)

class DetalleFacturaInline(admin.TabularInline):
    model = DetalleFactura
    extra = 1

@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    inlines = (DetalleFacturaInline,)
    list_display = ('numero_factura', 'propiedad', 'fecha_emision', 'fecha_vencimiento', 'total_calculado', 'monto_pagado_total', 'estado', 'esta_pagada')
    list_filter = ('estado', 'propiedad__complejo', 'fecha_emision')
    search_fields = ('numero_factura', 'propiedad__numero_identificador')
    readonly_fields = ('numero_factura',)

@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'activo')
    list_filter = ('tipo', 'activo')

@admin.register(Recaudo)
class RecaudoAdmin(admin.ModelAdmin):
    list_display = ('factura', 'fecha_pago', 'monto_pagado', 'metodo_pago')
    list_filter = ('metodo_pago', 'fecha_pago', 'factura__propiedad__complejo')
    search_fields = ('factura__numero_factura', 'referencia')

@admin.register(ConfiguracionFinanciera)
class ConfiguracionFinancieraAdmin(admin.ModelAdmin):
    list_display = ('complejo', 'propiedad', 'dia_corte', 'tasa_interes_mora_diaria')





@admin.register(ContratoFinanciero)
class ContratoFinancieroAdmin(admin.ModelAdmin):
    list_display = ('propiedad_persona', 'plan', 'adelanto', 'es_pago_contado', 'estado', 'cuotas_facturadas')
    list_filter = ('estado', 'es_pago_contado')
    search_fields = ('propiedad_persona__persona__email', 'propiedad_persona__persona__nombres')
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "propiedad_persona":
            # Filtramos para que solo aparezcan los responsables principales activos
            kwargs["queryset"] = PropiedadPersona.objects.filter(es_principal=True, estado='activo')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(CargoAdicional)
class CargoAdicionalAdmin(admin.ModelAdmin):
    list_display = ('concepto', 'propiedad', 'monto', 'fecha_registro', 'procesado')
    list_filter = ('procesado', 'fecha_registro', 'concepto')
    search_fields = ('propiedad__numero_identificador', 'observaciones')