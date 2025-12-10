from django.db import models
from django.conf import settings
from complejos.models import Propiedad, Complejo, PropiedadPersona 
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
    
    # Vinculación con Contrato Financiero (Nuevo)
    contrato = models.ForeignKey(
        'ContratoFinanciero', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='facturas',
        help_text="Contrato financiero que generó esta factura (si aplica)"
    )

    @property
    def total_calculado(self):
        return sum(detalle.monto for detalle in self.detalles.all())

    @property
    def monto_pagado_total(self):
        return sum(recaudo.monto_pagado for recaudo in self.recaudos.all())

    @property
    def esta_pagada(self):
        return self.monto_pagado_total >= self.total_calculado

    @property
    def saldo_pendiente(self):
        return max(self.total_calculado - self.monto_pagado_total, 0)
    
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
    descripcion = models.CharField(max_length=255, blank=True, null=True, help_text="Descripción opcional del detalle (ej. Cuota 1/12)")

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


class ConfiguracionFinanciera(models.Model):
    """
    Define las "Reglas de Juego" automáticas para cada complejo.
    Centraliza la configuración para no tener números mágicos en el código.
    """
    nombre = models.CharField(max_length=100, default="Configuración Estándar", help_text="Nombre para identificar esta configuración")
    es_personalizada = models.BooleanField(default=False, help_text="Si es True, es específica de un contrato y no se muestra en listas generales")
    complejo = models.ForeignKey(Complejo, on_delete=models.CASCADE, related_name='configuraciones_financieras')
    propiedad = models.OneToOneField(Propiedad, on_delete=models.CASCADE, null=True, blank=True, related_name='configuracion_financiera_especifica')
    
    # Automatización de Fechas
    dia_corte = models.PositiveIntegerField(default=1, help_text="Día del mes en que se generan las facturas automáticamente (1-28)")
    dias_vencimiento = models.PositiveIntegerField(default=15, help_text="Días de gracia después del corte antes de declarar mora")
    
    # Reglas de Cobranza
    tasa_interes_mora_diaria = models.DecimalField(max_digits=5, decimal_places=3, default=0.033, help_text="Interés diario % (ej. 0.033% diario ≈ 1% mensual)")
    bloquear_servicios_con_deuda = models.BooleanField(default=False, help_text="Si es True, impide reservar amenidades si hay facturas vencidas")
    
    # Plan Base
    plan_mantenimiento_default = models.ForeignKey(
        'PlanCuota', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='config_mantenimiento',
        help_text="Plan de cuotas (Gasto Común) que se aplica si el residente no tiene plan personalizado"
    )

    def __str__(self):
        tipo = f"Específica para {self.propiedad}" if self.propiedad else "Global del Complejo"
        return f"Configuración Financiera ({tipo}) - {self.complejo.nombre}"


class ContratoFinanciero(models.Model):
    """
    Maneja los cobros específicos de cada persona que NO son gastos comunes.
    Ej: El pago mensual de su alquiler o la cuota de compra del departamento.
    """
    TIPO_CHOICES = [
        ('ALQUILER', 'Alquiler / Renta Mensual'),
        ('FINANCIAMIENTO', 'Financiamiento / Compra a Plazos'),
    ]
    
    ESTADO_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('PAUSADO', 'Pausado'),
        ('FINALIZADO', 'Finalizado'), # Cuando termina de pagar la compra o se va el inquilino
        ('CANCELADO', 'Cancelado'),
    ]


    # Relación con el contrato legal existente
    propiedad_persona = models.OneToOneField(PropiedadPersona, on_delete=models.CASCADE, related_name='contrato_financiero')
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='ALQUILER')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='ACTIVO')
    
    # Nuevo enfoque: Configuración personalizada
    configuracion_personalizada = models.BooleanField(default=False, help_text="Si es True, usa una configuración financiera específica (fechas, tasas). Si es False, usa la configuración del complejo.")
    
    # PLAN PERSONALIZADO (Reemplaza a ConceptoContrato)
    plan = models.ForeignKey('PlanCuota', on_delete=models.PROTECT, null=True, blank=True, help_text="Plan de cuotas (Conceptos de cobro) específico para este contrato")

    # CONFIGURACIÓN FINANCIERA (Reemplaza los overrides directos)
    configuracion = models.ForeignKey('ConfiguracionFinanciera', on_delete=models.PROTECT, null=True, blank=True, help_text="Configuración financiera específica (fechas, tasas). Si es null y configuracion_personalizada=False, usa la del complejo.")

    # Reglas de Tiempo
    fecha_inicio_pago = models.DateField(help_text="Fecha desde la cual se empieza a facturar")
    
    # Finanzas
    adelanto = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, help_text="Monto pagado al inicio (Entrada/Pie)")
    
    # Campos exclusivos para COMPRA (Financiamiento)
    es_pago_contado = models.BooleanField(default=False, help_text="Si es compra al contado (sin cuotas)")
    monto_cuota = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Monto fijo de la cuota mensual para financiamiento")
    numero_cuotas_totales = models.PositiveIntegerField(null=True, blank=True, help_text="Solo para financiamiento: Total de cuotas pactadas (ej. 12, 24)")
    cuotas_facturadas = models.PositiveIntegerField(default=0, help_text="Contador de cuotas ya generadas")
    monto_pendiente = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Deuda total restante del inmueble tras el adelanto")

    def __str__(self):
        return f"Finanzas - {self.propiedad_persona.persona.email}"

    def es_vigente(self):
        """Helper para saber si debemos generarle factura este mes"""
        if self.estado != 'ACTIVO':
            return False
        
        # Si es compra al contado, normalmente no genera facturas mensuales recurrentes de 'cuota',
        # salvo que tenga conceptos de mantenimiento asociados.
        # Aquí asumimos que si es contado, el flujo de "cuotas" no aplica, pero el mantenimiento sí.
        
        # Si es financiamiento y ya se cobraron todas las cuotas...
        if self.numero_cuotas_totales and self.cuotas_facturadas >= self.numero_cuotas_totales:
            # OJO: Si tiene mantenimiento, sigue vigente.
            # Esta lógica deberá refinarse para separar Cuota Propiedad vs Gastos Comunes.
            # Por ahora lo dejamos genérico.
            pass
            
        return True

    @property
    def tiene_informacion_compra(self):
        """Devuelve True si hay datos relevantes de compra/venta para mostrar."""
        return (self.monto_pendiente and self.monto_pendiente > 0) or \
               (self.adelanto and self.adelanto > 0) or \
               (self.numero_cuotas_totales and self.numero_cuotas_totales > 0)

    @property
    def configuracion_efectiva(self):
        """
        Devuelve la configuración financiera efectiva (personalizada o del complejo).
        """
        if self.configuracion_personalizada and self.configuracion:
            return self.configuracion
        return self.propiedad_persona.propiedad.complejo.configuraciones_financieras.first()

    @property
    def cuotas_pagadas(self):
        """
        Calcula cuántas cuotas se han pagado realmente basándose en facturas pagadas
        asociadas a este contrato.
        """
        return self.facturas.filter(estado='PAGADA').count()

    @property
    def porcentaje_progreso_cuotas(self):
        """Calcula el porcentaje de cuotas pagadas (0-100) basado en pagos reales."""
        if not self.numero_cuotas_totales or self.numero_cuotas_totales == 0:
            return 0
        porcentaje = (self.cuotas_pagadas / self.numero_cuotas_totales) * 100
        return min(porcentaje, 100) # Cap at 100

    def delete(self, *args, **kwargs):
        # Capturamos el plan antes de borrar el contrato
        plan_to_check = self.plan
        super().delete(*args, **kwargs)
        
        # Lógica de "Borrado Inteligente":
        # Si el plan era exclusivo de este contrato (no usado por nadie más)
        # Y NO es el plan default del complejo, entonces lo borramos también.
        if plan_to_check:
             # Verificar si el plan quedó huérfano (nadie más lo usa)
             is_used_by_others = ContratoFinanciero.objects.filter(plan=plan_to_check).exists()
             
             # Verificar si es un plan maestro de configuración default
             # (Usamos el related_name 'config_mantenimiento')
             is_default_config = ConfiguracionFinanciera.objects.filter(plan_mantenimiento_default=plan_to_check).exists()
             
             if not is_used_by_others and not is_default_config:
                 print(f"Borrado Inteligente: Eliminando plan huérfano '{plan_to_check.nombre}' tras borrar contrato.")
                 plan_to_check.delete()

class CargoAdicional(models.Model):
    """
    Cargos extra puntuales (Multas, Reservas manuales, Servicios extra)
    que se agregan a la próxima factura.
    """
    propiedad = models.ForeignKey(Propiedad, on_delete=models.CASCADE, related_name='cargos_adicionales')
    concepto = models.ForeignKey(ConceptoCobro, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    
    fecha_registro = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True, null=True)
    
    procesado = models.BooleanField(default=False, help_text="True si ya fue incluido en una factura")
    factura_asociada = models.ForeignKey(Factura, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargos_origen')

    def __str__(self):
        return f"Cargo: {self.concepto.nombre} - {self.propiedad} (${self.monto})"