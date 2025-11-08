from django.db import models
from django.conf import settings
from complejos.models import Complejo

class Aviso(models.Model):
    """
    Modelo para representar un aviso o notificación en el sistema.
    """
    class TipoAviso(models.TextChoices):
        GENERAL = 'GENERAL', 'General'
        MANTENIMIENTO = 'MANTENIMIENTO', 'Mantenimiento'
        URGENTE = 'URGENTE', 'Urgente'

    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='avisos_creados_nuevos'
    )
    
    complejo = models.ForeignKey(
        Complejo,
        on_delete=models.CASCADE,
        related_name='avisos_nuevos'
    )
    
    tipo_aviso = models.CharField(
        max_length=20,
        choices=TipoAviso.choices,
        default=TipoAviso.GENERAL
    )
    
    leido_por = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='avisos_leidos_nuevos',
        blank=True
    )

    def __str__(self):
        return self.titulo

    class Meta:
        ordering = ['-fecha_creacion']
