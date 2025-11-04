from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError

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
    residentes = models.ManyToManyField(settings.AUTH_USER_MODEL, through='PropiedadPersona', related_name='propiedades_habitadas')

    def __str__(self):
        return f'{self.numero_identificador} ({self.complejo.nombre})'

    def clean(self):
        super().clean()
        if self.pk: # Check if the instance is saved
            # 2. If there are multiple owners, the sum of their percentages must be 100%.
            propietarios = self.personas_asociadas.filter(tipo_relacion__in=['propietario', 'co-propietario'])
            if propietarios.count() > 1:
                total_porcentaje = sum(p.porcentaje_propiedad for p in propietarios if p.porcentaje_propiedad is not None)
                if total_porcentaje != 100:
                    raise ValidationError(f'La suma de los porcentajes de los propietarios debe ser 100%. Actualmente es {total_porcentaje}%.')

            # 4. The occupancy status of the property should be consistent.
            if self.personas_asociadas.filter(tipo_relacion='inquilino', estado='activo').exists():
                if self.estado_ocupacion != 'ocupado':
                    self.estado_ocupacion = 'ocupado'
            elif self.estado_ocupacion == 'ocupado' and not self.personas_asociadas.filter(tipo_relacion='inquilino', estado='activo').exists():
                self.estado_ocupacion = 'disponible'

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class PropiedadPersona(models.Model):
    TIPO_RELACION_CHOICES = (
        ('propietario', 'Propietario'),
        ('inquilino', 'Inquilino'),
        ('co-propietario', 'Co-propietario'),
        ('avalista', 'Avalista'),
    )
    ESTADO_CHOICES = (
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
    )

    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE, related_name='personas_asociadas')
    persona = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='propiedades_asociadas')
    tipo_relacion = models.CharField(max_length=20, choices=TIPO_RELACION_CHOICES)
    porcentaje_propiedad = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Para co-propietarios")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True, help_text="Solo para inquilinos")
    es_principal = models.BooleanField(default=False, help_text="Para identificar el responsable principal")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')

    def __str__(self):
        return f'{self.propiedad} - {self.persona} ({self.tipo_relacion})'

    def clean(self):
        super().clean()
        # 1. A property cannot have multiple active "principal" tenants at the same time.
        if self.tipo_relacion == 'inquilino' and self.es_principal and self.estado == 'activo':
            if PropiedadPersona.objects.filter(
                propiedad=self.propiedad,
                tipo_relacion='inquilino',
                es_principal=True,
                estado='activo'
            ).exclude(pk=self.pk).exists():
                raise ValidationError('Ya existe un inquilino principal activo para esta propiedad.')

        # 3. A person cannot be both an owner and a tenant of the same property simultaneously.
        if self.tipo_relacion in ['propietario', 'co-propietario']:
            if PropiedadPersona.objects.filter(
                propiedad=self.propiedad,
                persona=self.persona,
                tipo_relacion='inquilino'
            ).exists():
                raise ValidationError('Esta persona ya es inquilino de esta propiedad.')
        
        if self.tipo_relacion == 'inquilino':
            if PropiedadPersona.objects.filter(
                propiedad=self.propiedad,
                persona=self.persona,
                tipo_relacion__in=['propietario', 'co-propietario']
            ).exists():
                raise ValidationError('Esta persona ya es propietaria de esta propiedad.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)