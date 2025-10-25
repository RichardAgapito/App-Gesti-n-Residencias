from django.db import models
from django.conf import settings

class Amenidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

class Complejo(models.Model):
    TIPO_CHOICES = (
        ('residencial', 'Residencial'),
        ('condominio', 'Condominio'),
    )
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    )
    nombre = models.CharField(max_length=100)
    calle = models.CharField(max_length=255)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    numero_total_unidades = models.PositiveIntegerField()
    amenidades = models.ManyToManyField(Amenidad)
    administrador_responsable = models.CharField(max_length=100)
    telefono_contacto = models.CharField(max_length=20)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')

    def __str__(self):
        return self.nombre

class Propiedad(models.Model):
    TIPO_PROPIEDAD_CHOICES = (
        ('departamento', 'Departamento'),
        ('casa', 'Casa'),
    )
    ESTADO_OCUPACION_CHOICES = (
        ('disponible', 'Disponible'),
        ('ocupado', 'Ocupado'),
        ('mantenimiento', 'En mantenimiento'),
    )
    complejo = models.ForeignKey(Complejo, on_delete=models.CASCADE, related_name='propiedades')
    numero_identificador = models.CharField(max_length=20, help_text='Ej: "101", "A-5", "Torre 2 - 304"')
    tipo = models.CharField(max_length=20, choices=TIPO_PROPIEDAD_CHOICES)
    area = models.DecimalField(max_digits=8, decimal_places=2)
    numero_habitaciones = models.PositiveIntegerField()
    numero_banos = models.PositiveIntegerField()
    piso_nivel = models.CharField(max_length=10)
    valor_estimado = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado_ocupacion = models.CharField(max_length=20, choices=ESTADO_OCUPACION_CHOICES, default='disponible')
    residente_actual = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='propiedades_habitadas'
    )

    def __str__(self):
        return f'{self.numero_identificador} ({self.complejo.nombre})'