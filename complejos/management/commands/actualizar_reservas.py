from django.core.management.base import BaseCommand
from django.utils import timezone
from complejos.models import Reserva

class Command(BaseCommand):
    help = 'Actualiza el estado de las reservas completadas.'

    def handle(self, *args, **options):
        now = timezone.now()
        reservas_a_completar = Reserva.objects.filter(
            estado='confirmada',
            fecha_fin__lte=now
        )

        count = reservas_a_completar.update(estado='completada')

        self.stdout.write(self.style.SUCCESS(f'Se completaron {count} reservas.'))
