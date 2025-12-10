from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import datetime

class Amenidad(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    capacidad = models.PositiveIntegerField(default=1, help_text="Capacidad máxima de personas")
    reglas = models.TextField(blank=True, null=True, help_text="Reglas de uso de la amenidad")
    hora_inicio = models.TimeField(default=datetime.time(8, 0))
    hora_fin = models.TimeField(default=datetime.time(22, 0))

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
    telefono_contacto = models.CharField(
        max_length=9,
        validators=[RegexValidator(regex=r'^\d{9}$', message='El número de teléfono debe tener exactamente 9 dígitos.')]
    )
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
    residentes = models.ManyToManyField('users.CustomUser', through='PropiedadPersona', related_name='propiedades_habitadas')

    def __str__(self):
        return f'{self.numero_identificador} ({self.complejo.nombre})'

    def clean(self):
        super().clean()

    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.full_clean()
        super().save(*args, **kwargs)

class PropiedadPersona(models.Model):
    TIPO_RELACION_CHOICES = (
        ('propietario', 'Propietario'),
        ('inquilino', 'Inquilino'),
        ('co-propietario', 'Co-propietario'),
        ('co-inquilino', 'Co-inquilino'),
    )
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    )
    PORCENTAJE_PROPIEDAD_CHOICES = (
        (100.00, '100%'),
        (50.00, '50%'),
    )

    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE, related_name='personas_asociadas')
    persona = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='propiedades_asociadas')
    tipo_relacion = models.CharField(max_length=20, choices=TIPO_RELACION_CHOICES)
    porcentaje_propiedad = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Para co-propietarios", choices=PORCENTAJE_PROPIEDAD_CHOICES)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True, help_text="Solo para inquilinos")
    es_principal = models.BooleanField(default=False, help_text="Para identificar el responsable principal")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')

    def __str__(self):
        return f'{self.propiedad} - {self.persona} ({self.tipo_relacion})'

    def save(self, *args, **kwargs):
        # Auto-asignar es_principal si es el primero
        if self.estado == 'activo' and not self.es_principal:
            # Verificar si ya existe un principal activo para esta propiedad
            # Excluimos self.pk por si es una actualización del mismo objeto
            existe_principal = PropiedadPersona.objects.filter(
                propiedad=self.propiedad,
                es_principal=True,
                estado='activo'
            ).exclude(pk=self.pk).exists()
            
            if not existe_principal:
                self.es_principal = True

        super().save(*args, **kwargs)
        propiedad = self.propiedad
        if propiedad.personas_asociadas.filter(tipo_relacion__in=['inquilino', 'propietario'], estado='activo').exists():
            if propiedad.estado_ocupacion != 'ocupado':
                propiedad.estado_ocupacion = 'ocupado'
                propiedad.save()
        else:
            if propiedad.estado_ocupacion != 'disponible':
                propiedad.estado_ocupacion = 'disponible'
                propiedad.save()

class Reserva(models.Model):
    ESTADO_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
        ('completada', 'Completada'),
        ('bloqueada', 'Bloqueada'),
    )

    amenidad = models.ForeignKey(Amenidad, on_delete=models.CASCADE, related_name='reservas')
    complejo = models.ForeignKey(Complejo, on_delete=models.CASCADE, related_name='reservas', null=True, blank=True)
    residente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reservas', null=True, blank=True)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.estado == 'bloqueada':
            return f'Horario bloqueado para {self.amenidad.nombre}'
        return f'Reserva de {self.amenidad.nombre} por {self.residente.email}'
 
