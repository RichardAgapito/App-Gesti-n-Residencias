from django.db import models
from django.conf import settings
from complejos.models import Propiedad, Complejo
from django.utils import timezone
from datetime import datetime

class PlanCuota(models.Model):
    class Frecuencia(models.TextChoices):
        MENSUAL = 'M', 'Mensual'
        TRIMESTRAL = 'T', 'Trimestral'
        SEMESTRAL = 'S', 'Semestral'

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    frecuencia = models.CharField(max_length=1, choices=Frecuencia.choices, default=Frecuencia.MENSUAL)
    activo = models.BooleanField(default=True)
    complejo = models.ForeignKey(Complejo, on_delete=models.SET_NULL, null=True, blank=True, related_name='planes_cuota')
    def __str__(self):
        return self.nombre

    @property
    def monto_total(self):
        from django.db.models import Sum
        total = self.planconceptocobro_set.aggregate(Sum('monto'))['monto__sum']
        return total or 0

class ConceptoCobro(models.Model):
    class Tipo(models.TextChoices):
        ORDINARIO = 'ORDINARIO', 'Ordinario'
        EXTRAORDINARIO = 'EXTRAORDINARIO', 'Extraordinario'

    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    obligatorio = models.BooleanField(default=True)
    complejo = models.ForeignKey(Complejo, on_delete=models.SET_NULL, null=True, blank=True, related_name='conceptos_cobro')

    def __str__(self):
        return self.nombre

class PlanConceptoCobro(models.Model):
    plan_cuota = models.ForeignKey(PlanCuota, on_delete=models.CASCADE)
    concepto_cobro = models.ForeignKey(ConceptoCobro, on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto específico para este concepto en este plan")
    orden = models.PositiveIntegerField(default=1, help_text="Orden en que aparece en la factura")
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('plan_cuota', 'concepto_cobro')
        ordering = ['orden']

    def __str__(self):
        return f"{self.plan_cuota.nombre} - {self.concepto_cobro.nombre}: ${self.monto}"

class Factura(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PAGADA = 'PAGADA', 'Pagada'
        VENCIDA = 'VENCIDA', 'Vencida'
        CANCELADA = 'CANCELADA', 'Cancelada'
        ANULADA = 'ANULADA', 'Anulada'

    numero_factura = models.CharField(max_length=20, unique=True)
    propiedad = models.ForeignKey(Propiedad, on_delete=models.PROTECT, related_name='facturas')
    plan_cuota = models.ForeignKey(PlanCuota, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.TextField(blank=True, null=True)

    @property
    def total_calculado(self):
        return sum(detalle.monto for detalle in self.detalles.all())

    @property
    def monto_pagado_total(self):
        return sum(recaudo.monto_pagado for recaudo in self.recaudos.all())

    @property
    def esta_pagada(self):
        return self.monto_pagado_total >= self.total_calculado
    
    def _update_factura_estado(self):
        # Evitar modificar estados terminales
        if self.estado in [self.Estado.CANCELADA, self.Estado.ANULADA]:
            return
        
        # Lógica para actualizar el estado
        if self.monto_pagado_total >= self.total_calculado and self.total_calculado > 0:
            if self.estado != self.Estado.PAGADA:
                self.estado = self.Estado.PAGADA
                self.save(update_fields=['estado'])
        elif self.estado == self.Estado.PAGADA:
            # Si estaba PAGADA pero ya no lo está (ej. se eliminó un recaudo), vuelve a PENDIENTE
            self.estado = self.Estado.PENDIENTE
            self.save(update_fields=['estado'])
        elif self.estado not in [self.Estado.PENDIENTE, self.Estado.VENCIDA]:
            # Si no está pagada y no está en un estado terminal, asegúrate de que sea PENDIENTE
            self.estado = self.Estado.PENDIENTE
            self.save(update_fields=['estado'])



    def __str__(self):
        return f"Factura {self.numero_factura} - {self.propiedad}"

    def save(self, *args, **kwargs):
        if not self.numero_factura:
            today_str = timezone.now().strftime('%Y%m%d')
            last_factura = Factura.objects.filter(numero_factura__startswith=f'F-{today_str}').order_by('-numero_factura').first()
            
            if last_factura:
                last_seq = int(last_factura.numero_factura.split('-')[-1])
                new_seq = last_seq + 1
            else:
                new_seq = 1
            
            self.numero_factura = f'F-{today_str}-{new_seq:04d}'
        super().save(*args, **kwargs)

class DetalleFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name='detalles')
    concepto_cobro = models.ForeignKey(ConceptoCobro, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.concepto_cobro.nombre} - {self.monto}"

class MetodoPago(models.Model):
    class Tipo(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Efectivo'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'
        TARJETA = 'TARJETA', 'Tarjeta'
        CHEQUE = 'CHEQUE', 'Cheque'

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    cuenta_banco = models.CharField(max_length=50, blank=True, null=True)
    activo = models.BooleanField(default=True)
    comision = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    def __str__(self):
        return self.nombre

class Recaudo(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name='recaudos')
    fecha_pago = models.DateField()
    monto_pagado = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT)
    referencia = models.CharField(max_length=100, blank=True, null=True)
    usuario_registro = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    observaciones = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Recaudo de {self.monto_pagado} para {self.factura.numero_factura}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.factura._update_factura_estado() # Update the factura's status

    def delete(self, *args, **kwargs):
        factura_to_update = self.factura
        super().delete(*args, **kwargs)
        factura_to_update._update_factura_estado() # Update the factura's status after deletion