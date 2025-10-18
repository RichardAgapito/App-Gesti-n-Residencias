from django.db import models
from django.conf import settings
from comunidades.models import Comunidad, Propiedad

class Visitante(models.Model):
    class TipoDocumento(models.TextChoices):
        DNI = 'DNI', 'DNI'
        CARNET_EXTRANJERIA = 'CARNET_EXTRANJERIA', 'Carnet de Extranjería'
        PASAPORTE = 'PASAPORTE', 'Pasaporte'

    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices)
    numero_documento = models.CharField(max_length=20)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)

    fecha_visita = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField(null=True, blank=True) # La salida puede registrarse después

    
    residente_visitado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='visitas_recibidas'
    )
    comunidad = models.ForeignKey(Comunidad, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.nombres} {self.apellidos} - Visita a {self.residente_visitado.username}'