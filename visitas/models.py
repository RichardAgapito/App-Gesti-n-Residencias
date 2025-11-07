from django.db import models
from users.models import CustomUser
from complejos.models import Propiedad

class Visitante(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('DNI', 'DNI'),
        ('Pasaporte', 'Pasaporte'),
        ('Carnet Extranjeria', 'Carnet de Extranjería'),
    ]
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('bloqueado', 'Bloqueado'),
    ]

    tipo_documento = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES)
    numero_documento = models.CharField(max_length=20, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15, blank=True)
    foto_capturada = models.ImageField(upload_to='visitantes/', blank=True, null=True)
    es_frecuente = models.BooleanField(default=False)
    fecha_registro_sistema = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='activo')

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

class Visita(models.Model):
    MOTIVO_VISITA_CHOICES = [
        ('social', 'Social'),
        ('proveedor', 'Proveedor'),
        ('delivery', 'Delivery'),
        ('mudanza', 'Mudanza'),
        ('tecnico', 'Técnico'),
    ]
    ESTADO_CHOICES = [
        ('dentro', 'Dentro'),
        ('salio', 'Salió'),
        ('no_autorizado', 'No Autorizado'),
    ]

    visitante = models.ForeignKey(Visitante, on_delete=models.CASCADE)
    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE)
    residente_autoriza = models.ForeignKey(CustomUser, related_name='visitas_autorizadas', on_delete=models.SET_NULL, null=True, blank=True)
    fecha_hora_ingreso = models.DateTimeField()
    fecha_hora_salida = models.DateTimeField(null=True, blank=True)
    motivo_visita = models.CharField(max_length=20, choices=MOTIVO_VISITA_CHOICES)
    placa_vehiculo = models.CharField(max_length=10, blank=True)
    cantidad_acompanantes = models.PositiveIntegerField(default=0)
    autorizado_previamente = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)
    usuario_registra = models.ForeignKey(CustomUser, related_name='visitas_registradas', on_delete=models.CASCADE)
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='dentro')

    def __str__(self):
        return f"Visita de {self.visitante} a {self.propiedad}"

class PreAutorizacion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('usado', 'Usado'),
        ('vencido', 'Vencido'),
        ('cancelado', 'Cancelado'),
    ]

    residente = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE)
    nombre_visitante = models.CharField(max_length=200)
    documento_visitante = models.CharField(max_length=20)
    fecha_hora_esperada = models.DateTimeField()
    vigencia_desde = models.DateTimeField()
    vigencia_hasta = models.DateTimeField()
    es_recurrente = models.BooleanField(default=False)
    dias_semana = models.CharField(max_length=50, blank=True, help_text='Ej: lunes,martes,viernes')
    usado = models.BooleanField(default=False)
    fecha_uso = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='pendiente')

    def __str__(self):
        return f"Pre-autorización para {self.nombre_visitante} en {self.propiedad}"