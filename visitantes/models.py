# visitantes/models.py
from django.db import models
from django.conf import settings
from comunidades.models import Comunidad, Propiedad

class Visitante(models.Model):
    # Opciones para el tipo de documento
    class TipoDocumento(models.TextChoices):
        DNI = 'DNI', 'DNI'
        CARNET_EXTRANJERIA = 'CARNET_EXTRANJERIA', 'Carnet de Extranjería'
        PASAPORTE = 'PASAPORTE', 'Pasaporte'

    # Datos del visitante
    tipo_documento = models.CharField(max_length=20, choices=TipoDocumento.choices)
    numero_documento = models.CharField(max_length=20)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)

    # Datos de la visita
    fecha_visita = models.DateField()
    hora_entrada = models.TimeField()
    hora_salida = models.TimeField(null=True, blank=True) # La salida puede registrarse después

    # --- Conexiones Clave ---
    # Residente al que visita
    residente_visitado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='visitas_recibidas'
    )
    # Comunidad donde se registra la visita (para separar los datos)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.nombres} {self.apellidos} - Visita a {self.residente_visitado.username}'