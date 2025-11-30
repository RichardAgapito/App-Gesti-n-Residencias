from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

from finanzas.models import Factura, DetalleFactura, ConfiguracionFinanciera, ConceptoCobro

class Command(BaseCommand):
    help = 'Actualiza estados de facturas (Vencimientos) y calcula intereses por mora.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('--- Iniciando Actualización Financiera ---'))
        
        today = timezone.localdate()
        
        # Obtenemos todas las configuraciones activas
        configs = ConfiguracionFinanciera.objects.select_related('complejo').all()

        if not configs.exists():
            self.stdout.write(self.style.WARNING('No hay configuraciones financieras definidas.'))
            return

        for config in configs:
            complejo = config.complejo
            self.stdout.write(f"\nProcesando Complejo: {complejo.nombre}")

            # ---------------------------------------------------------
            # TAREA 1: Detectar Vencimientos (PENDIENTE -> VENCIDA)
            # ---------------------------------------------------------
            # Buscamos facturas pendientes cuya fecha de vencimiento ya pasó (es menor a hoy)
            facturas_vencidas_hoy = Factura.objects.filter(
                propiedad__complejo=complejo,
                estado='PENDIENTE',
                fecha_vencimiento__lt=today
            )
            
            count_vencidas = facturas_vencidas_hoy.update(estado='VENCIDA')
            if count_vencidas > 0:
                self.stdout.write(self.style.WARNING(f"  -> {count_vencidas} facturas pasaron a estado VENCIDA."))

            # ---------------------------------------------------------
            # TAREA 2: Calcular Mora (Solo para facturas VENCIDA)
            # ---------------------------------------------------------
            if config.tasa_interes_mora_diaria > 0:
                facturas_en_mora = Factura.objects.filter(
                    propiedad__complejo=complejo,
                    estado='VENCIDA'
                ).prefetch_related('detalles') # Optimizamos la consulta

                # Nos aseguramos de tener un Concepto de Cobro para la mora
                # Si no existe, lo creamos automáticamente
                concepto_mora, _ = ConceptoCobro.objects.get_or_create(
                    nombre="Interés por Mora",
                    complejo=complejo,
                    defaults={
                        'tipo': 'EXTRAORDINARIO',
                        'descripcion': 'Recargo automático por pago fuera de fecha',
                        'obligatorio': True
                    }
                )

                for factura in facturas_en_mora:
                    # Calcular días de atraso
                    dias_atraso = (today - factura.fecha_vencimiento).days
                    
                    if dias_atraso <= 0:
                        continue # Por seguridad, aunque el filtro ya lo debería evitar

                    # Calcular la base imponible (Total original SIN la mora anterior)
                    # Excluimos el concepto de mora para no cobrar interés sobre interés (anatocismo)
                    subtotal_original = sum(
                        d.monto for d in factura.detalles.all() 
                        if d.concepto_cobro != concepto_mora
                    )

                    # Fórmula: Capital * (TasaDiaria/100) * Días
                    tasa_decimal = config.tasa_interes_mora_diaria / 100
                    interes_acumulado = subtotal_original * tasa_decimal * dias_atraso
                    
                    # Redondeamos a 2 decimales
                    interes_acumulado = interes_acumulado.quantize(Decimal('0.01'))

                    # Actualizar o Crear el detalle de mora
                    # Buscamos si esta factura ya tiene una línea de mora
                    detalle_mora = factura.detalles.filter(concepto_cobro=concepto_mora).first()

                    if detalle_mora:
                        # Si ya existe, solo actualizamos el monto si cambió
                        if detalle_mora.monto != interes_acumulado:
                            detalle_mora.monto = interes_acumulado
                            detalle_mora.save()
                            # self.stdout.write(f"    -> Factura {factura.numero_factura}: Mora actualizada a ${interes_acumulado}")
                    else:
                        # Si es el primer día de mora, creamos la línea
                        DetalleFactura.objects.create(
                            factura=factura,
                            concepto_cobro=concepto_mora,
                            monto=interes_acumulado
                        )
                        self.stdout.write(f"    -> Factura {factura.numero_factura}: Se aplicó primera mora de ${interes_acumulado}")

        self.stdout.write(self.style.SUCCESS('\n--- Actualización Finalizada ---'))