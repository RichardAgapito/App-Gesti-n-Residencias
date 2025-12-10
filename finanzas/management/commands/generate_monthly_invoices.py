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
                            # El plan cuota cabecera será None inicialmente, se asigna si hay contrato
                            plan_cuota=None, 
                            fecha_emision=today,
                            fecha_vencimiento=fecha_vencimiento,
                            estado='PENDIENTE',
                            observaciones=f"Facturación Mensual - {today.strftime('%B %Y')}"
                        )
                        
                        total_acumulado = 0

                        # --- PASO B: (ELIMINADO) No hay cobro de Mantenimiento por defecto ---
                        # Solo se cobra si hay Contrato Financiero o Cargos Adicionales.


                        # --- PASO 1: Determinar Plan de Cuota a Facturar ---
                        # Estrategia: "Exclusive OR"
                        # 1. Por defecto, usamos el plan del de la configuración (Global)
                        plan_a_usar = config_actual.plan_mantenimiento_default
                        contrato_fin = None

                        # 2. Buscamos si tiene Contrato Financiero ACTIVO
                        contrato_candidate = ContratoFinanciero.objects.filter(
                            propiedad_persona=contrato_residencial,
                            estado='ACTIVO'
                        ).first()

                        if contrato_candidate and contrato_candidate.es_vigente():
                            contrato_fin = contrato_candidate
                            # Si el contrato tiene un plan específico, ESTE anula al default
                            if contrato_fin.plan:
                                plan_a_usar = contrato_fin.plan

                        # --- PASO 2: Generar Detalles de la Factura (El Cobro) ---
                        if plan_a_usar:
                            # Asignamos el plan a la cabecera
                            factura.plan_cuota = plan_a_usar
                            
                            # Si identificamos un contrato financiero, lo vinculamos
                            if contrato_fin:
                                factura.contrato = contrato_fin
                                
                            factura.save(update_fields=['plan_cuota', 'contrato'])

                            # Generamos los items del plan elegido
                            conceptos_del_plan = PlanConceptoCobro.objects.filter(
                                plan_cuota=plan_a_usar
                            ).select_related('concepto_cobro')

                            for item in conceptos_del_plan:
                                DetalleFactura.objects.create(
                                    factura=factura,
                                    concepto_cobro=item.concepto_cobro,
                                    monto=item.monto
                                )
                                total_acumulado += item.monto
                        
                        # --- PASO 3: Procesar Lógica del Contrato (Saldos / Cuotas) ---
                        if contrato_fin:
                            # Vincular contrato a la factura si no se hizo antes
                            if not factura.contrato:
                                factura.contrato = contrato_fin
                                factura.save(update_fields=['contrato'])

                            if contrato_fin.tipo == 'FINANCIAMIENTO':
                                # --- NUEVA LÓGICA DE FINANCIAMIENTO ---
                                # Si tiene cuota definida, la agregamos como Item a la factura
                                if contrato_fin.monto_cuota and contrato_fin.monto_cuota > 0:
                                    
                                    # Verificar si todavía faltan cuotas por facturar
                                    # Usamos cuotas_facturadas como límite
                                    if not contrato_fin.numero_cuotas_totales or contrato_fin.cuotas_facturadas < contrato_fin.numero_cuotas_totales:
                                        
                                        # Buscar o crear Concepto de Cobro para la cuota
                                        # Idealmente esto debería estar parametrizado, pero para evitar fallos creamos uno genérico
                                        from finanzas.models import ConceptoCobro
                                        concepto_cuota, _ = ConceptoCobro.objects.get_or_create(
                                            nombre="Cuota Financiamiento",
                                            defaults={'descripcion': "Cuota mensual de financiamiento de propiedad"}
                                        )

                                        # Crear Detalle
                                        DetalleFactura.objects.create(
                                            factura=factura,
                                            concepto_cobro=concepto_cuota,
                                            monto=contrato_fin.monto_cuota,
                                            descripcion=f"Cuota {contrato_fin.cuotas_facturadas + 1} de {contrato_fin.numero_cuotas_totales or '?'}"
                                        )
                                        total_acumulado += contrato_fin.monto_cuota
                                        
                                        # Actualizar contadores del contrato
                                        contrato_fin.cuotas_facturadas += 1
                                        
                                        # Reducir saldo (Solo por el monto de la cuota, NO por el total de la factura)
                                        if contrato_fin.monto_pendiente:
                                            contrato_fin.monto_pendiente = max(0, contrato_fin.monto_pendiente - contrato_fin.monto_cuota)

                                        # Verificar finalización
                                        if contrato_fin.numero_cuotas_totales and contrato_fin.cuotas_facturadas >= contrato_fin.numero_cuotas_totales:
                                            contrato_fin.estado = 'FINALIZADO'
                                            self.stdout.write(self.style.SUCCESS(f"    -> Fin contrato compra para {propiedad}"))
                                        
                                        contrato_fin.save()
                                else:
                                    self.stdout.write(self.style.WARNING(f"    -> Contrato Financiamiento para {propiedad} no tiene monto_cuota definido."))
                        
                        # --- PASO 4: Agregar Cargos Adicionales Pendientes ---
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