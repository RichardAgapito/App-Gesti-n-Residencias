from django.core.management.base import BaseCommand
from complejos.models import Amenidad

class Command(BaseCommand):
    help = 'Populates existing amenities with default data for new fields'

    def handle(self, *args, **kwargs):
        amenities_data = {
            'Piscina': {
                'descripcion': 'Piscina al aire libre con área para niños.',
                'capacidad': 20,
                'reglas': 'Ducharse antes de entrar. No se permiten alimentos ni bebidas en el área de la piscina.',
                'horario_disponibilidad': 'Martes a Domingo de 10:00 a 19:00',
            },
            'Gimnasio': {
                'descripcion': 'Gimnasio equipado con máquinas de cardio y pesas.',
                'capacidad': 10,
                'reglas': 'Uso obligatorio de toalla. Limpiar las máquinas después de su uso.',
                'horario_disponibilidad': 'Lunes a Domingo de 6:00 a 22:00',
            },
            'Salón de eventos': {
                'descripcion': 'Amplio salón para eventos privados y reuniones.',
                'capacidad': 50,
                'reglas': 'Se requiere un depósito de seguridad. La limpieza corre por cuenta del residente.',
                'horario_disponibilidad': 'Viernes a Domingo de 12:00 a 23:00',
            },
            'Cancha de Tenis': {
                'descripcion': 'Cancha de tenis de superficie dura.',
                'capacidad': 4,
                'reglas': 'Uso de calzado deportivo adecuado. Reservas de 1 hora por día por residente.',
                'horario_disponibilidad': 'Lunes a Domingo de 8:00 a 21:00',
            }
        }

        for amenidad_nombre, data in amenities_data.items():
            try:
                amenidad = Amenidad.objects.get(nombre=amenidad_nombre)
                amenidad.descripcion = data['descripcion']
                amenidad.capacidad = data['capacidad']
                amenidad.reglas = data['reglas']
                amenidad.horario_disponibilidad = data['horario_disponibilidad']
                amenidad.save()
                self.stdout.write(self.style.SUCCESS(f'Successfully updated amenity: {amenidad_nombre}'))
            except Amenidad.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'Amenity not found: {amenidad_nombre}'))
