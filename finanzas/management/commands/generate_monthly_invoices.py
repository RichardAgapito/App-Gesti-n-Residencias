from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta

from complejos.models import Complejo, PropiedadPersona
from finanzas.models import (
    Factura, DetalleFactura, ConfiguracionFinanciera, 
    ContratoFinanciero, PlanConceptoCobro, CargoAdicional
)

class Command(BaseCommand):
    help = 'Genera facturas mensuales inteligentes (Mantenimiento + Contratos Específicos)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la generación aunque no sea el día de corte',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando Generación de Facturas ---'))
        
        today = timezone.localdate()
        
        # Recorremos todos los complejos que tengan configuración financiera
        configs = ConfiguracionFinanciera.objects.select_related('complejo', 'plan_mantenimiento_default').all()

        if not configs.exists():
            self.stdout.write(self.style.WARNING('No se encontraron configuraciones financieras. Crea una en el admin primero.'))
            return

        for config in configs:
            complejo = config.complejo
            self.stdout.write(f"\nProcesando Complejo: {complejo.nombre}")

            # 1. Validación de Día de Corte
            if not options['force'] and today.day != config.dia_corte:
                self.stdout.write(self.style.NOTICE(f"  -> Saltando: Hoy es día {today.day}, el corte es el {config.dia_corte}."))
                continue

            # 2. Obtener residentes activos (Propietarios o Inquilinos principales)
            # Filtramos solo los que tienen contrato activo con la propiedad
            residentes_activos = PropiedadPersona.objects.filter(
                propiedad__complejo=complejo,
                estado='activo',
                es_principal=True  # Solo facturamos al responsable principal
            ).select_related('propiedad', 'persona')

            count_facturas = 0

            for contrato_residencial in residentes_activos:
                propiedad = contrato_residencial.propiedad
                usuario = contrato_residencial.persona
                
                # 3. Verificar si ya existe factura para este mes y año para esta propiedad
                # Esto evita duplicados si corres el script dos veces
                if Factura.objects.filter(
                    propiedad=propiedad, 
                    fecha_emision__year=today.year, 
                    fecha_emision__month=today.month
                ).exists():
                    # self.stdout.write(f"  -> Factura ya existe para {propiedad}")
                    continue

                try:
                    with transaction.atomic():
                        # --- PASO 0: Determinar Configuración a usar (Específica vs Global) ---
                        # Buscamos configuracion especifica de la propiedad
                        config_especifica = getattr(propiedad, 'configuracion_financiera_especifica', None)
                        
                        # Usar especifica si existe, sino la global (config del loop)
                        config_actual = config_especifica if config_especifica else config

                        # --- PASO A: Crear la Cabecera de la Factura ---
                        fecha_vencimiento = today + timedelta(days=config_actual.dias_vencimiento)
                        
                        factura = Factura.objects.create(
                            propiedad=propiedad,
                            # El plan cuota cabecera será el de mantenimiento base (informativo)
                            plan_cuota=config_actual.plan_mantenimiento_default, 
                            fecha_emision=today,
                            fecha_vencimiento=fecha_vencimiento,
                            estado='PENDIENTE',
                            observaciones=f"Facturación Mensual - {today.strftime('%B %Y')}"
                        )
                        
                        total_acumulado = 0

                        # --- PASO B: Agregar Conceptos de Mantenimiento (Gasto Común) ---
                        if config_actual.plan_mantenimiento_default:
                            conceptos_base = PlanConceptoCobro.objects.filter(
                                plan_cuota=config_actual.plan_mantenimiento_default,
                                # No filtar por activo=True aqui plan_cuota.planconceptocobro_set.all() ?
                                # Asumiendo que el PlanConceptoCobro no tiene campo activo, pero el PlanCuota si.
                            ).select_related('concepto_cobro')

                            for item in conceptos_base:
                                DetalleFactura.objects.create(
                                    factura=factura,
                                    concepto_cobro=item.concepto_cobro,
                                    monto=item.monto
                                )
                                total_acumulado += item.monto

                        # --- PASO C: Buscar Contratos Financieros (Alquiler / Compra) ---
                        contrato_fin = ContratoFinanciero.objects.filter(
                            propiedad_persona=contrato_residencial,
                            estado='ACTIVO'
                        ).first()

                        if contrato_fin and contrato_fin.es_vigente():
                            # Usar los conceptos del plan de pago del contrato
                            if contrato_fin.plan_pago:
                                conceptos_contrato = PlanConceptoCobro.objects.filter(
                                    plan_cuota=contrato_fin.plan_pago
                                ).select_related('concepto_cobro')
                                
                                for item in conceptos_contrato:
                                    DetalleFactura.objects.create(
                                        factura=factura,
                                        concepto_cobro=item.concepto_cobro,
                                        monto=item.monto
                                    )
                                    total_acumulado += item.monto
                                
                                # Actualizar estados del contrato
                                if contrato_fin.tipo == 'FINANCIAMIENTO':
                                    contrato_fin.cuotas_facturadas += 1
                                    
                                    # Reducir saldo si aplica
                                    if contrato_fin.saldo_pendiente and total_acumulado > 0:
                                        # Nota: Aquí estamos asumiendo que TODO el monto va al capital, 
                                        # lo cual podría no ser cierto si hay intereses. 
                                        # Simplificación: reducir saldo por el monto total del plan contrato.
                                        monto_contrato_total = sum(c.monto for c in conceptos_contrato)
                                        contrato_fin.saldo_pendiente -= monto_contrato_total

                                    if contrato_fin.numero_cuotas_totales and contrato_fin.cuotas_facturadas >= contrato_fin.numero_cuotas_totales:
                                        contrato_fin.estado = 'FINALIZADO'
                                        self.stdout.write(self.style.SUCCESS(f"    -> Fin contrato compra para {propiedad}"))
                                    
                                    contrato_fin.save()
                        
                        # --- PASO D: Agregar Cargos Adicionales Pendientes (Multas / Extras) ---
                        cargos_pendientes = CargoAdicional.objects.filter(
                            propiedad=propiedad,
                            procesado=False
                        )
                        
                        if cargos_pendientes.exists():
                            for cargo in cargos_pendientes:
                                DetalleFactura.objects.create(
                                    factura=factura,
                                    concepto_cobro=cargo.concepto,
                                    monto=cargo.monto
                                )
                                total_acumulado += cargo.monto
                                
                                # Marcar como procesado
                                cargo.procesado = True
                                cargo.factura_asociada = factura
                                cargo.save()
                                self.stdout.write(f"    -> Cargo agregado: {cargo.monto}")

                        factura.save()
                        
                        count_facturas += 1
                        self.stdout.write(f"  -> Generada Factura {factura.numero_factura} para {propiedad} (${total_acumulado})")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  -> Error generando factura para {propiedad}: {str(e)}"))

            self.stdout.write(self.style.SUCCESS(f"Complejo {complejo.nombre}: {count_facturas} facturas generadas."))

        self.stdout.write(self.style.SUCCESS('\n--- Proceso Finalizado ---'))