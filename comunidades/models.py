# comunidades/models.py
from django.db import models
from django.conf import settings # Necesario para conectar con el modelo User de forma segura

# Modelo para la Residencia/Condominio en general
class Comunidad(models.Model):
    nombre = models.CharField(max_length=100, help_text="Ej: Condominio El Sol")
    direccion = models.CharField(max_length=255)
    fecha_creacion = models.DateTimeField(auto_now_add=True) # Guarda la fecha y hora de creación automáticamente

    def __str__(self):
        return self.nombre

# Modelo para cada Casa o Departamento dentro de una Comunidad
class Propiedad(models.Model):
    # Opciones definidas para el tipo de contrato del residente
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

    # --- Conexiones Clave (Foreign Keys) ---
    
    # Conexión con la Comunidad a la que pertenece. Si se borra la comunidad, se borran sus propiedades.
    comunidad = models.ForeignKey(Comunidad, on_delete=models.CASCADE, related_name='propiedades')
    
    # Conexión con el usuario que vive ahí.
    residente_actual = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, # Si se borra el usuario, este campo queda vacío (NULL), pero la propiedad no se borra.
        null=True, # Permite que el campo esté vacío en la base de datos.
        blank=True, # Permite que el campo esté vacío en los formularios.
        related_name='propiedades_habitadas'
    )

    def __str__(self):
        return f'{self.numero_identificador} ({self.comunidad.nombre})'