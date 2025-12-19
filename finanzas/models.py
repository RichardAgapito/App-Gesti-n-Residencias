from django.db import models
from django.conf import settings
from complejos.models import Propiedad, Complejo, PropiedadPersona 
from django.utils import timezone
from datetime import datetime
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.core.exceptions import ValidationError

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
    """
    Catálogo de métodos de pago disponibles en el sistema.
    Define QUÉ métodos están habilitados (ej: "Visa", "Yape", "Efectivo Caja").
    """
    
    class Tipo(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Efectivo'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia Bancaria'
        TARJETA = 'TARJETA', 'Tarjeta de Crédito/Debito'
        BILLETERA_DIGITAL = 'BILLETERA_DIGITAL', 'Billetera Digital (Yape, Plin, etc.)'
        DEPOSITO_BANCARIO = 'DEPOSITO_BANCARIO', 'Depósito Bancario'
    
    nombre = models.CharField(
        max_length=100,
        help_text="Nombre del método (ej: 'Visa Crédito', 'Yape', 'Efectivo Administración')"
    )
    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    activo = models.BooleanField(default=True)
    
    # Configuración específica del método
    requiere_aprobacion = models.BooleanField(
        default=False,
        help_text="Si es True, el pago queda en estado 'pendiente de aprobación'"
    )
    
    # Información bancaria (para transferencias/depósitos)
    banco = models.CharField(max_length=100, blank=True, null=True)
    numero_cuenta = models.CharField(max_length=50, blank=True, null=True)
    tipo_cuenta = models.CharField(
        max_length=20,
        choices=[('CORRIENTE', 'Corriente'), ('AHORROS', 'Ahorros'), ('CCI', 'CCI')],
        blank=True,
        null=True
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"
        ordering = ['tipo', 'nombre']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nombre}"

class Recaudo(models.Model):
    """
    Registro de un pago recibido. Ahora incluye campos específicos según el método de pago.
    """
    
    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente de Aprobación'
        APROBADO = 'APROBADO', 'Aprobado'
        RECHAZADO = 'RECHAZADO', 'Rechazado'

    
    # Relaciones básicas
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name='recaudos')
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT)
    
    # Información general del pago
    fecha_pago = models.DateField(help_text="Fecha en que se realizó el pago")
    monto_pagado = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.APROBADO
    )
    
    # ==================== CAMPOS ESPECÍFICOS POR TIPO ====================
    
    # EFECTIVO
    recibido_por = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Nombre de quien recibió el efectivo (Gerente, Administrador, etc.)"
    )
    
    # TARJETA (Crédito/Débito)
    numero_tarjeta = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Número de tarjeta (se enmascarará al guardar)"
    )
    tarjeta_titular = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Nombre del titular como aparece en la tarjeta"
    )
    tarjeta_tipo = models.CharField(
        max_length=20,
        choices=[('VISA', 'Visa'), ('MASTERCARD', 'Mastercard'), ('AMEX', 'American Express'), ('OTRO', 'Otro')],
        blank=True,
        null=True
    )

    
    fecha_expiracion = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\d{2}/\d{2}$', 'Formato inválido. Use MM/YY')],
        help_text="Formato MM/YY"
    )
    codigo_cvv = models.CharField(
        max_length=3,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\d{3}$', 'El CVV debe tener 3 dígitos')],
        help_text="Código de seguridad"
    )
    
    # TRANSFERENCIA / DEPÓSITO BANCARIO
    banco_origen = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Banco desde donde se realizó la transferencia"
    )
    numero_operacion = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Número de operación o referencia bancaria"
    )
    
    # BILLETERA DIGITAL (Yape, Plin, etc.)
    billetera_numero_transaccion = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="ID de transacción de la billetera digital"
    )
    billetera_numero_celular = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[RegexValidator(r'^\+?[\d\s\-]{7,20}$', 'Formato de teléfono inválido')],
        help_text="Número de celular asociado a la billetera"
    )
    comprobante_imagen = models.ImageField(
        upload_to='comprobantes/%Y/%m/',
        blank=True,
        null=True,
        help_text="Captura de pantalla del comprobante"
    )
    
    # ==================== CAMPOS COMUNES ====================
    
    # Auditoría y control
    usuario_registro = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recaudos_registrados',
        help_text="Usuario que registró el pago"
    )
    usuario_aprobacion = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recaudos_aprobados',
        help_text="Usuario que aprobó el pago"
    )
    fecha_aprobacion = models.DateTimeField(blank=True, null=True)
    motivo_rechazo = models.TextField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Recaudo"
        verbose_name_plural = "Recaudos"
        ordering = ['-fecha_pago', '-created_at']
        indexes = [
            models.Index(fields=['fecha_pago', 'estado']),
            models.Index(fields=['factura', 'estado']),
        ]
    
    def __str__(self):
        return f"Recaudo {self.id} - {self.monto_pagado} ({self.get_estado_display()})"
    
    def clean(self):
        """Validaciones específicas según el tipo de método de pago"""
        super().clean()
        
        # Validar que el monto no exceda el saldo de la factura (si existe factura)
        if self.factura:
            saldo_actual = self.factura.saldo_pendiente
            # Si estamos editando, sumar el monto anterior al saldo
            if self.pk:
                try:
                    recaudo_anterior = Recaudo.objects.get(pk=self.pk)
                    saldo_actual += recaudo_anterior.monto_pagado
                except Recaudo.DoesNotExist:
                    pass
            
            if self.monto_pagado > saldo_actual:
                raise ValidationError({
                    'monto_pagado': f'El monto excede el saldo pendiente de la factura (${saldo_actual})'
                })

        # Si no hay metodo de pago asignado aun (puede pasar en forms iniciales), salir
        if not self.metodo_pago:
            return

        tipo_metodo = self.metodo_pago.tipo
        
        # Validaciones para EFECTIVO
        if tipo_metodo == MetodoPago.Tipo.EFECTIVO:
            if not self.recibido_por:
                raise ValidationError({
                    'recibido_por': 'Para pagos en efectivo debe indicar quién recibió el dinero'
                })
        
        # Validaciones para TARJETA
        if tipo_metodo == MetodoPago.Tipo.TARJETA:
            if not self.numero_tarjeta:
                raise ValidationError({
                    'numero_tarjeta': 'Debe ingresar el número de tarjeta'
                })
            else:
                 # Validar longitud mínima
                 if len(self.numero_tarjeta) < 13: # Basic validation
                     raise ValidationError({'numero_tarjeta': 'Número de tarjeta inválido'})

            if not self.tarjeta_titular:
                raise ValidationError({
                    'tarjeta_titular': 'Debe ingresar el nombre del titular de la tarjeta'
                })
            if not self.fecha_expiracion:
                raise ValidationError({'fecha_expiracion': 'La fecha de expiración es requerida'})
            
            if not self.codigo_cvv:
                raise ValidationError({'codigo_cvv': 'El código CVV es requerido'})
        # Validaciones para TRANSFERENCIA/DEPÓSITO
        if tipo_metodo in [MetodoPago.Tipo.TRANSFERENCIA, MetodoPago.Tipo.DEPOSITO_BANCARIO]:
            if not self.numero_operacion:
                raise ValidationError({
                    'numero_operacion': 'Debe ingresar el número de operación o referencia'
                })
        
        # Validaciones para BILLETERA DIGITAL
        if tipo_metodo == MetodoPago.Tipo.BILLETERA_DIGITAL:
            if not self.billetera_numero_transaccion and not self.comprobante_imagen:
                raise ValidationError({
                    'billetera_numero_transaccion': 'Debe ingresar el número de transacción o subir un comprobante'
                })
        
    
    def save(self, *args, **kwargs):
        # Enmascarar tarjeta si es necesario
        if self.numero_tarjeta and len(self.numero_tarjeta) > 4 and not all(c == '*' for c in self.numero_tarjeta[:-4]):
             last_digits = self.numero_tarjeta[-4:]
             mask = '*' * (len(self.numero_tarjeta) - 4)
             self.numero_tarjeta = f"{mask}{last_digits}"
        
        # Enmascarar CVV
        if self.codigo_cvv:
             self.codigo_cvv = "***"

        # Si el método requiere aprobación, establecer estado inicial si es nuevo
        if not self.pk and self.metodo_pago.requiere_aprobacion:
            self.estado = self.Estado.PENDIENTE
        
        super().save(*args, **kwargs)
        
        # Actualizar estado de la factura solo si está aprobado (y no borrado)
        if self.estado == self.Estado.APROBADO and self.factura:
            self.factura._update_factura_estado()
    
    def delete(self, *args, **kwargs):
        factura_to_update = self.factura
        super().delete(*args, **kwargs)
        if factura_to_update:
            factura_to_update._update_factura_estado()
    
    def aprobar(self, usuario):
        """Aprueba el recaudo"""
        if self.estado != self.Estado.PENDIENTE:
            raise ValidationError('Solo se pueden aprobar recaudos pendientes')
        
        self.estado = self.Estado.APROBADO
        self.usuario_aprobacion = usuario
        self.fecha_aprobacion = timezone.now()
        self.save()
    
    def rechazar(self, usuario, motivo):
        """Rechaza el recaudo"""
        if self.estado != self.Estado.PENDIENTE:
            raise ValidationError('Solo se pueden rechazar recaudos pendientes')
        
        self.estado = self.Estado.RECHAZADO
        self.usuario_aprobacion = usuario
        self.fecha_aprobacion = timezone.now()
        self.motivo_rechazo = motivo
        self.save()
    
    def revertir(self, usuario, motivo):
        """Revierte un recaudo aprobado"""
        if self.estado != self.Estado.APROBADO:
            raise ValidationError('Solo se pueden revertir recaudos aprobados')
        
        # Al revertir, lo marcamos como rechazado pero con el motivo específico
        self.estado = self.Estado.RECHAZADO 
        self.usuario_aprobacion = usuario
        self.motivo_rechazo = f"REVERTIDO: {motivo}"
        self.save()
        
        # Actualizar estado de la factura
        self.factura._update_factura_estado()
    
    @property
    def requiere_aprobacion(self):
        """Verifica si el recaudo requiere aprobación"""
        return self.metodo_pago.requiere_aprobacion
    
    @property
    def puede_ser_aprobado(self):
        """Verifica si el recaudo puede ser aprobado"""
        return self.estado == self.Estado.PENDIENTE


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

