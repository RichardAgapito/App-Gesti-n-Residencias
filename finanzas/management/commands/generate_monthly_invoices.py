from django.core.management.base import BaseCommand
from django.db import transaction, models
from django.utils import timezone
from datetime import timedelta

from complejos.models import Complejo, PropiedadPersona
from finanzas.models import PlanCuota, PlanConceptoCobro, Factura, DetalleFactura

class Command(BaseCommand):
    help = 'Generates monthly invoices for all occupied properties in each complex.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--complejo_id',
            type=int,
            help='Specify a complex ID to generate invoices for a single complex.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting monthly invoice generation...'))

        today = timezone.localdate()
        complejo_id = options.get('complejo_id')

        complejos_to_process = Complejo.objects.all()
        if complejo_id:
            complejos_to_process = Complejo.objects.filter(id=complejo_id)
            if not complejos_to_process.exists():
                self.stdout.write(self.style.ERROR(f'Complex with ID {complejo_id} not found.'))
                return

        for complejo in complejos_to_process:
            self.stdout.write(self.style.MIGRATE_HEADING(f'Processing Complex: {complejo.nombre}'))

            # Get active PlanCuota for this complex (assuming one active plan per complex for simplicity)
            plan_to_apply = PlanCuota.objects.filter(complejo=complejo, activo=True).first()

            if not plan_to_apply:
                self.stdout.write(self.style.WARNING(f'  No active plan found for {complejo.nombre}. Skipping.'))
                continue

            plan_conceptos = plan_to_apply.planconceptocobro_set.filter(activo=True)
            if not plan_conceptos.exists():
                self.stdout.write(self.style.WARNING(f'  Plan "{plan_to_apply.nombre}" has no active concepts. Skipping.'))
                continue

            # Get occupied properties
            occupied_properties = PropiedadPersona.objects.filter(
                propiedad__complejo=complejo,
                estado='activo'
            ).select_related('propiedad')

            if not occupied_properties.exists():
                self.stdout.write(self.style.NOTICE(f'  No occupied properties found. Skipping.'))
                continue

            for pp in occupied_properties:
                propiedad = pp.propiedad
                
                # Check if an invoice for this property and plan already exists for the current month
                if Factura.objects.filter(propiedad=propiedad, plan_cuota=plan_to_apply, fecha_emision__month=today.month, fecha_emision__year=today.year).exists():
                    self.stdout.write(self.style.NOTICE(f'    Invoice already exists for property {propiedad} this month. Skipping.'))
                    continue

                due_date = today + timedelta(days=15)
                
                try:
                    with transaction.atomic():
                        factura = Factura.objects.create(
                            propiedad=propiedad,
                            plan_cuota=plan_to_apply,
                            fecha_vencimiento=due_date,
                            monto_total=0, # Will be updated
                            observaciones=f"Factura mensual según {plan_to_apply.nombre} para {today.strftime('%B %Y')}"
                        )
                        
                        total_monto_factura = 0
                        for plan_concepto in plan_conceptos:
                            DetalleFactura.objects.create(
                                factura=factura,
                                concepto_cobro=plan_concepto.concepto_cobro,
                                monto=plan_concepto.monto,
                                descripcion=f"{plan_concepto.concepto_cobro.nombre}"
                            )
                            total_monto_factura += plan_concepto.monto
                        
                        factura.monto_total = total_monto_factura
                        factura.save()
                        self.stdout.write(self.style.SUCCESS(f'      Generated invoice {factura.numero_factura} for property {propiedad}.'))

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'      Error generating invoice for property {propiedad}: {e}'))

        self.stdout.write(self.style.SUCCESS('Monthly invoice generation finished.'))
