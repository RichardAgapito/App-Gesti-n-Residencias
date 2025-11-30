from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta

from complejos.models import Complejo, PropiedadPersona
from finanzas.models import (
    Factura, DetalleFactura, ConfiguracionFinanciera, 
    ContratoFinanciero, PlanConceptoCobro
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
                        # --- PASO A: Crear la Cabecera de la Factura ---
                        # Calculamos vencimiento según la configuración del complejo
                        fecha_vencimiento = today + timedelta(days=config.dias_vencimiento)
                        
                        factura = Factura.objects.create(
                            propiedad=propiedad,
                            plan_cuota=config.plan_mantenimiento_default, # Referencia al plan base
                            fecha_emision=today,
                            fecha_vencimiento=fecha_vencimiento,
                            estado='PENDIENTE',
                            observaciones=f"Facturación Mensual - {today.strftime('%B %Y')}"
                        )

                        total_acumulado = 0

                        # --- PASO B: Agregar Conceptos de Mantenimiento (Para TODOS) ---
                        if config.plan_mantenimiento_default:
                            conceptos_base = PlanConceptoCobro.objects.filter(
                                plan_cuota=config.plan_mantenimiento_default,
                                activo=True
                            ).select_related('concepto_cobro')

                            for item in conceptos_base:
                                DetalleFactura.objects.create(
                                    factura=factura,
                                    concepto_cobro=item.concepto_cobro,
                                    monto=item.monto,
                                    # descripcion=item.concepto_cobro.nombre # (Opcional si tu modelo tiene descripción)
                                )
                                total_acumulado += item.monto

                        # --- PASO C: Buscar Contratos Financieros Específicos (Alquiler/Compra) ---
                        # Buscamos si este residente tiene un contrato financiero activo
                        contrato_fin = ContratoFinanciero.objects.filter(
                            propiedad_persona=contrato_residencial,
                            estado='ACTIVO'
                        ).first()

                        if contrato_fin and contrato_fin.es_vigente():
                            # Crear un concepto de cobro "al vuelo" o usar uno genérico si prefieres
                            # Aquí asumimos que tienes un ConceptoCobro genérico para "Alquiler/Cuota"
                            # O creamos el detalle directamente.
                            
                            # NOTA: Para que esto funcione perfecto, asegúrate de tener un ConceptoCobro
                            # llamado "Cuota Contrato" o similar en la BD, o créalo dinámicamente.
                            from finanzas.models import ConceptoCobro
                            concepto_extra, _ = ConceptoCobro.objects.get_or_create(
                                nombre=f"Cuota {contrato_fin.get_tipo_display()}",
                                defaults={'tipo': 'ORDINARIO', 'complejo': complejo}
                            )

                            DetalleFactura.objects.create(
                                factura=factura,
                                concepto_cobro=concepto_extra,
                                monto=contrato_fin.monto_cuota,
                                # descripcion=f"Cuota correspondiente al contrato {contrato_fin.id}"
                            )
                            total_acumulado += contrato_fin.monto_cuota

                            # Si es financiamiento (compra), actualizamos el contador
                            if contrato_fin.tipo == 'FINANCIAMIENTO':
                                contrato_fin.cuotas_facturadas += 1
                                if contrato_fin.saldo_pendiente:
                                    contrato_fin.saldo_pendiente -= contrato_fin.monto_cuota
                                
                                # Auto-finalizar si completó cuotas
                                if contrato_fin.numero_cuotas_totales and contrato_fin.cuotas_facturadas >= contrato_fin.numero_cuotas_totales:
                                    contrato_fin.estado = 'FINALIZADO'
                                    self.stdout.write(self.style.SUCCESS(f"    -> ¡Contrato de compra finalizado para {propiedad}!"))
                                
                                contrato_fin.save()

                        # --- Guardar Total ---
                        # Como tu modelo Factura calculaba el total dinámicamente con una @property,
                        # no necesitamos guardar 'monto_total' si eliminaste el campo en migraciones anteriores.
                        # Si aún tienes el campo monto_total en la BD para caché:
                        # factura.monto_total = total_acumulado
                        factura.save()
                        
                        count_facturas += 1
                        self.stdout.write(f"  -> Generada Factura {factura.numero_factura} para {propiedad} (${total_acumulado})")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  -> Error generando factura para {propiedad}: {str(e)}"))

            self.stdout.write(self.style.SUCCESS(f"Complejo {complejo.nombre}: {count_facturas} facturas generadas."))

        self.stdout.write(self.style.SUCCESS('\n--- Proceso Finalizado ---'))