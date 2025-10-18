from django.db import models
from django.conf import settings 

class Comunidad(models.Model):
    nombre = models.CharField(max_length=100, help_text="Ej: Condominio El Sol")
    direccion = models.CharField(max_length=255)
    fecha_creacion = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return self.nombre

class Propiedad(models.Model):
    class TipoContrato(models.TextChoices):
        PROPIETARIO = 'PROPIETARIO', 'Propietario'
        INQUILINO = 'INQUILINO', 'Inquilino'
        TEMPORAL = 'TEMPORAL', 'Temporal'

    numero_identificador = models.CharField(max_length=20, help_text="Ej: Departamento 101, Casa 25B")
    
    tipo_contrato = models.CharField(
        max_length=20, 
        choices=TipoContrato.choices, 
        default=TipoContrato.PROPIETARIO
    )

    
    comunidad = models.ForeignKey(Comunidad, on_delete=models.CASCADE, related_name='propiedades')
    
    residente_actual = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='propiedades_habitadas'
    )

    def __str__(self):
        return f'{self.numero_identificador} ({self.comunidad.nombre})'