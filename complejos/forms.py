from django import forms
from .models import Amenidad, Complejo, Propiedad, PropiedadPersona, Reserva
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from django.utils import timezone
from visitas.models import PreAutorizacion
from django.core.validators import RegexValidator


from finanzas.models import PlanCuota, ContratoFinanciero, ConfiguracionFinanciera
from django.db import transaction

class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.persona.__str__() if obj.persona else obj.email

class AmenidadForm(forms.ModelForm):
    class Meta:
        model = Amenidad
        fields = '__all__'

class ComplejoForm(forms.ModelForm):
    amenidades = forms.ModelMultipleChoiceField(
        queryset=Amenidad.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Complejo
        fields = '__all__'

    def clean_telefono_contacto(self):
        telefono = self.cleaned_data.get('telefono_contacto')
        if telefono:

            if not telefono.isdigit():
                raise ValidationError("Este campo solo debe contener números.")

            if len(telefono) != 9:
                raise ValidationError("El número de teléfono debe tener exactamente 9 dígitos.")
        return telefono

class PropiedadForm(forms.ModelForm):
    class Meta:
        model = Propiedad
        exclude = ['numero_identificador', 'residentes', 'tipo', 'complejo']

class CrearPropiedadesMultiplesForm(forms.ModelForm):
    cantidad = forms.IntegerField(min_value=1, label='Cantidad de propiedades a crear')

    class Meta:
        model = Propiedad
        exclude = ['complejo', 'numero_identificador', 'residentes', 'tipo']

class EditarPropiedadForm(forms.ModelForm):
    class Meta:
        model = Propiedad
        fields = ['area', 'numero_habitaciones', 'numero_banos', 'piso_nivel', 'valor_estimado', 'estado_ocupacion']

    def clean(self):
        return self.cleaned_data

class PropiedadPersonaForm(forms.ModelForm):
    porcentaje_propiedad = forms.DecimalField(max_digits=5, decimal_places=2, required=False, widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        self.propiedad = kwargs.pop('propiedad', None)
        super().__init__(*args, **kwargs)
        
        active_residents = get_user_model().objects.filter(rol='RESIDENTE', is_active=True)
        
        persona_initial = None
        if self.instance and self.instance.pk:
            persona_initial = self.instance.persona

        self.fields['persona'] = forms.ModelChoiceField(
            queryset=active_residents,
            label="Persona",
            initial=persona_initial
        )

        persona2_initial = None



        self.fields['persona2'] = forms.ModelChoiceField(
            queryset=active_residents,
            required=False,
            label="Segunda Persona",
            initial=persona2_initial
        )

        if 'persona' in self.data:
            try:
                persona_id = int(self.data.get('persona'))
                self.fields['persona2'].queryset = active_residents.exclude(pk=persona_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.persona:
            self.fields['persona2'].queryset = active_residents.exclude(pk=self.instance.persona.pk)

    class Meta:
        model = PropiedadPersona
        fields = ['propiedad', 'persona', 'tipo_relacion', 'porcentaje_propiedad', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo_relacion = cleaned_data.get('tipo_relacion')
        persona = cleaned_data.get('persona')
        persona2 = cleaned_data.get('persona2')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        if tipo_relacion in ['co-propietario', 'co-inquilino']:
            if not persona2:
                self.add_error('persona2', 'Este campo es requerido para co-propietarios y co-inquilinos.')
            elif persona == persona2:
                self.add_error('persona2', 'La segunda persona no puede ser la misma que la primera.')

        if fecha_inicio and fecha_inicio < date.today():
            raise ValidationError({"fecha_inicio": "La fecha de inicio no puede ser anterior a la fecha actual."})

        if fecha_inicio and fecha_fin and fecha_fin < fecha_inicio + timedelta(days=30):
            raise ValidationError({"fecha_fin": "La fecha de fin no puede ser menor a 30 días después de la fecha de inicio."})


        if self.propiedad and persona:
            if tipo_relacion == 'inquilino' and cleaned_data.get('es_principal') and cleaned_data.get('estado') == 'activo':
                if PropiedadPersona.objects.filter(
                    propiedad=self.propiedad,
                    tipo_relacion='inquilino',
                    es_principal=True,
                    estado='activo'
                ).exists():
                    raise ValidationError('Ya existe un inquilino principal activo para esta propiedad.')

            if tipo_relacion in ['propietario', 'co-propietario']:
                if PropiedadPersona.objects.filter(
                    propiedad=self.propiedad,
                    persona=persona,
                    tipo_relacion='inquilino',
                    estado='activo'
                ).exists():
                    raise ValidationError('Esta persona ya es inquilino activo de esta propiedad.')
            
            if tipo_relacion == 'inquilino':
                if PropiedadPersona.objects.filter(
                    propiedad=self.propiedad,
                    persona=persona,
                    tipo_relacion__in=['propietario', 'co-propietario'],
                    estado='activo'
                ).exists():
                    raise ValidationError('Esta persona ya es propietaria activa de esta propiedad.')

            if tipo_relacion in ['co-propietario', 'co-inquilino']:
                co_relations = PropiedadPersona.objects.filter(
                    propiedad=self.propiedad,
                    tipo_relacion=tipo_relacion,
                    estado='activo'
                )
                if co_relations.count() >= 2:
                    raise ValidationError(f'No se pueden agregar más de 2 {tipo_relacion}s activos a esta propiedad.')

        return cleaned_data

class GlobalContratoForm(forms.ModelForm):
    persona = UserChoiceField(
        queryset=get_user_model().objects.filter(rol='RESIDENTE', is_active=True),
        label="Persona"
    )
    persona2 = UserChoiceField(
        queryset=get_user_model().objects.filter(rol='RESIDENTE', is_active=True),
        required=False,
        label="Segunda Persona"
    )

    class Meta:
        model = PropiedadPersona
        fields = ['propiedad', 'persona', 'tipo_relacion', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            base_classes = "w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-sm"
            
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = f"{base_classes} appearance-none"
            else:
                field.widget.attrs['class'] = base_classes

    def clean(self):
        cleaned_data = super().clean()
        propiedad = cleaned_data.get('propiedad')
        tipo_relacion = cleaned_data.get('tipo_relacion')
        persona = cleaned_data.get('persona')
        persona2 = cleaned_data.get('persona2')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        if tipo_relacion in ['co-propietario', 'co-inquilino']:
            if not persona2:
                self.add_error('persona2', 'Este campo es requerido para co-propietarios y co-inquilinos.')
            elif persona == persona2:
                self.add_error('persona2', 'La segunda persona no puede ser la misma que la primera.')

        if fecha_inicio and fecha_inicio < date.today():
            raise ValidationError({"fecha_inicio": "La fecha de inicio no puede ser anterior a la fecha actual."})


        if tipo_relacion in ['propietario', 'co-propietario']:
            cleaned_data['fecha_fin'] = None
        elif tipo_relacion in ['inquilino', 'co-inquilino']:
            if not fecha_fin:
                self.add_error('fecha_fin', 'La fecha de fin es requerida para los inquilinos.')
            elif fecha_inicio and fecha_fin < fecha_inicio + timedelta(days=30):
                self.add_error('fecha_fin', 'La fecha de fin no puede ser menor a 30 días después de la fecha de inicio.')

        if propiedad and persona:

            if tipo_relacion in ['propietario', 'co-propietario']:
                if PropiedadPersona.objects.filter(propiedad=propiedad, tipo_relacion='propietario', es_principal=True, estado='activo').exists():
                    raise ValidationError(f"La propiedad '{propiedad}' ya tiene un Propietario principal activo.")
            
            if tipo_relacion in ['inquilino', 'co-inquilino']:
                if PropiedadPersona.objects.filter(propiedad=propiedad, tipo_relacion='inquilino', es_principal=True, estado='activo').exists():
                    raise ValidationError(f"La propiedad '{propiedad}' ya tiene un Inquilino principal activo.")


            if tipo_relacion in ['propietario', 'co-propietario']:
                if PropiedadPersona.objects.filter(propiedad=propiedad, persona=persona, tipo_relacion='inquilino', estado='activo').exists():
                    raise ValidationError('Esta persona ya es inquilino activo de esta propiedad.')
            
            if tipo_relacion == 'inquilino':
                if PropiedadPersona.objects.filter(propiedad=propiedad, persona=persona, tipo_relacion__in=['propietario', 'co-propietario'], estado='activo').exists():
                    raise ValidationError('Esta persona ya es propietaria activa de esta propiedad.')

        return cleaned_data

class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['fecha_inicio', 'fecha_fin']
        widgets = {
            'fecha_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        self.amenidad = kwargs.pop('amenidad', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        if fecha_inicio and fecha_inicio < timezone.now():
            raise ValidationError("La fecha de inicio no puede ser en el pasado.")

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio.")

        if self.amenidad and fecha_inicio and fecha_fin:

            reservas_en_conflicto = Reserva.objects.filter(
                amenidad=self.amenidad,
                estado__in=['confirmada', 'bloqueada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            ).exists()

            if reservas_en_conflicto:
                raise ValidationError("Este horario ya no está disponible. Por favor, elige otro.")


            if fecha_inicio.time() < self.amenidad.hora_inicio:
                raise ValidationError(f"La hora de inicio no puede ser antes de la apertura de la amenidad ({self.amenidad.hora_inicio.strftime('%H:%M')}).")
            
            if fecha_fin.time() > self.amenidad.hora_fin:
                raise ValidationError(f"La hora de fin no puede ser después del cierre de la amenidad ({self.amenidad.hora_fin.strftime('%H:%M')}).")

        return cleaned_data

class AdminReservaForm(forms.ModelForm):
    residente = forms.ModelChoiceField(
        queryset=get_user_model().objects.filter(rol='RESIDENTE', is_active=True),
        label="Residente"
    )

    class Meta:
        model = Reserva
        fields = ['residente', 'amenidad', 'fecha_inicio', 'fecha_fin', 'estado']
        widgets = {
            'fecha_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        amenidad = cleaned_data.get('amenidad')

        if fecha_inicio and fecha_inicio < timezone.now():
            raise ValidationError("La fecha de inicio no puede ser en el pasado.")

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio.")

        if amenidad and fecha_inicio and fecha_fin:

            reservas_en_conflicto = Reserva.objects.filter(
                amenidad=amenidad,
                estado__in=['confirmada', 'bloqueada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            ).exclude(pk=self.instance.pk)

            if reservas_en_conflicto.exists():
                raise ValidationError("Este horario ya no está disponible. Por favor, elige otro.")


            if fecha_inicio.time() < amenidad.hora_inicio:
                raise ValidationError(f"La hora de inicio no puede ser antes de la apertura de la amenidad ({amenidad.hora_inicio.strftime('%H:%M')}).")
            
            if fecha_fin.time() > amenidad.hora_fin:
                raise ValidationError(f"La hora de fin no puede ser después del cierre de la amenidad ({amenidad.hora_fin.strftime('%H:%M')}).")

        return cleaned_data

class BloquearHorarioForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['fecha_inicio', 'fecha_fin']
        widgets = {
            'fecha_inicio': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        self.amenidad = kwargs.pop('amenidad', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        if fecha_inicio and fecha_inicio < timezone.now():
            raise ValidationError("La fecha de inicio no puede ser en el pasado.")

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio.")

        if self.amenidad and fecha_inicio and fecha_fin:

            reservas_en_conflicto = Reserva.objects.filter(
                amenidad=self.amenidad,
                estado__in=['confirmada', 'bloqueada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            ).exists()

            if reservas_en_conflicto:
                raise ValidationError("Este horario ya no está disponible. Por favor, elige otro.")


            if fecha_inicio.time() < self.amenidad.hora_inicio:
                raise ValidationError(f"La hora de inicio no puede ser antes de la apertura de la amenidad ({self.amenidad.hora_inicio.strftime('%H:%M')}).")
            
            if fecha_fin.time() > self.amenidad.hora_fin:
                raise ValidationError(f"La hora de fin no puede ser después del cierre de la amenidad ({self.amenidad.hora_fin.strftime('%H:%M')}).")

        return cleaned_data

class ResidentePreAutorizacionForm(forms.ModelForm):
    

    nombre_visitante = forms.CharField(
        label="Nombre del Visitante",
        validators=[
            RegexValidator(
                r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message="El nombre solo debe contener letras y espacios."
            )
        ]
    )


    numero_documento = forms.CharField(
        label="Documento del Visitante",
        validators=[
            RegexValidator(
                r'^\d{8}$',
                message="El número de documento debe contener 8 dígitos."
            )
        ],
        widget=forms.TextInput(attrs={
            'maxlength': '8'
        })
    )


    es_recurrente = forms.BooleanField(
        label="¿Es una visita recurrente?",
        required=False
    )
    

    DIAS_CHOICES = (
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado'),
        ('domingo', 'Domingo'),
    )
    

    dias_semana = forms.MultipleChoiceField(
        label="Días de la semana recurrentes",
        choices=DIAS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = PreAutorizacion
        fields = [
            'nombre_visitante', 
            'numero_documento',
            'fecha_hora_esperada', 
            'vigencia_desde', 
            'vigencia_hasta',
            'es_recurrente',
            'dias_semana',
        ]

        exclude = [
            'residente', 
            'propiedad', 
            'estado', 
            'usado', 
            'fecha_uso',
        ]
        widgets = {
            'fecha_hora_esperada': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'vigencia_desde': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'vigencia_hasta': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['numero_documento'].label = "Documento del Visitante"
        if self.instance and self.instance.pk:
            self.fields['numero_documento'].initial = self.instance.documento_visitante

            self.fields['es_recurrente'].initial = self.instance.es_recurrente
            if self.instance.dias_semana:

                self.fields['dias_semana'].initial = self.instance.dias_semana.split(',')

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('vigencia_desde')
        fecha_fin = cleaned_data.get('vigencia_hasta')
        fecha_esperada = cleaned_data.get('fecha_hora_esperada')

        if fecha_inicio and fecha_inicio < timezone.now():
            raise ValidationError("La vigencia de la autorización no puede empezar en el pasado.")
        
        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            raise ValidationError("La fecha de fin de vigencia debe ser posterior a la fecha de inicio.")

        if fecha_esperada and fecha_inicio and fecha_fin:
            if not (fecha_inicio <= fecha_esperada <= fecha_fin):
                raise ValidationError("La fecha esperada de la visita debe estar dentro del rango de vigencia.")
        es_recurrente = cleaned_data.get('es_recurrente')
        dias_semana = cleaned_data.get('dias_semana')
        
        if es_recurrente and not dias_semana:
            self.add_error('dias_semana', 'Si la visita es recurrente, debes seleccionar al menos un día.')
        
        cleaned_data['documento_visitante'] = cleaned_data.get('numero_documento')
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        instance.documento_visitante = self.cleaned_data.get('numero_documento')
        instance.nombre_visitante = self.cleaned_data.get('nombre_visitante')
        

        instance.es_recurrente = self.cleaned_data.get('es_recurrente')
        
        dias_semana_list = self.cleaned_data.get('dias_semana')
        if dias_semana_list:


            instance.dias_semana = ",".join(dias_semana_list)
        else:
            instance.dias_semana = ""
        
        if commit:
            instance.save()
        return instance

class ContratoUnificadoForm(PropiedadPersonaForm):
    # Campos extra para la parte financiera
    finanzas_cuotas = forms.IntegerField(
        min_value=1, required=False, 
        label="Número de Cuotas",
        help_text="Solo si es financiamento a plazos. Deje vacío si es al contado o indefinido."
    )
    finanzas_adelanto = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False, initial=0,
        label="Pago Adelantado / Entrada",
        help_text="Monto inicial pagado."
    )
    finanzas_es_contado = forms.BooleanField(
        required=False,
        label="¿Es pago al contado?",
        help_text="Marque si el residente paga el total de la propiedad en un solo acto."
    )
    configuracion_personalizada = forms.BooleanField(
        required=False, 
        label="Configuración Financiera Personalizada",
        help_text="Habilitar para agregar conceptos de cobro específicos (Alquiler, Mantenimiento, etc.) en el siguiente paso."
    )

    # Overrides Financial Fields
    finanzas_dia_corte = forms.IntegerField(
        min_value=1, max_value=28, required=False,
        label="Día de Corte Mensual",
        help_text="Override: Fija un día específico para generar la deuda."
    )
    finanzas_dias_vencimiento = forms.IntegerField(
        min_value=0, required=False,
        label="Días para Vencimiento",
        help_text="Override: Días extra después del corte antes de mora."
    )
    finanzas_tasa_mora = forms.DecimalField(
        min_value=0, max_digits=5, decimal_places=3, required=False,
        label="Tasa de Mora (%)",
        help_text="Override: Porcentaje de penalidad por atraso.",
        widget=forms.NumberInput(attrs={'step': '0.001'})
    )

    class Meta(PropiedadPersonaForm.Meta):
        fields = PropiedadPersonaForm.Meta.fields + ['propiedad']

    def save(self, commit=True):
        # Usamos una transacción para asegurar que ambos se creen o ninguno
        with transaction.atomic():
            # 1. Guardar la parte de PropiedadPersona (Legal)
            propiedad_persona = super().save(commit=True)

            # 2. Guardar la parte de ContratoFinanciero (Financiera)
            # Recuperar prop valor
            prop_valor = propiedad_persona.propiedad.valor_estimado or 0
            adelanto = self.cleaned_data.get('finanzas_adelanto') or 0
            es_contado = self.cleaned_data.get('finanzas_es_contado')
            
            # Si es contado, el adelanto es el valor total (automático)
            if es_contado:
                adelanto = prop_valor
            
            monto_pendiente = 0
            if propiedad_persona.tipo_relacion == 'propietario' and not es_contado:
               monto_pendiente = max(0, prop_valor - adelanto)

            # Overrides
            dia_corte = self.cleaned_data.get('finanzas_dia_corte')
            dias_venc = self.cleaned_data.get('finanzas_dias_vencimiento')
            tasa_mora = self.cleaned_data.get('finanzas_tasa_mora')

            # Crear contrato financiero vinculado
            cf = ContratoFinanciero.objects.create(
                propiedad_persona=propiedad_persona,
                fecha_inicio_pago=propiedad_persona.fecha_inicio,
                
                adelanto=adelanto,
                es_pago_contado=es_contado,
                numero_cuotas_totales=self.cleaned_data.get('finanzas_cuotas'),
                monto_pendiente=monto_pendiente,
                
                configuracion_personalizada=self.cleaned_data.get('configuracion_personalizada'),
                estado='ACTIVO',
                
                # Campos de override NO se pasan directamente al contrato ya
            )
            
            if self.cleaned_data.get('configuracion_personalizada'):
                # Crear configuración financiera personalizada
                # Crear configuración financiera personalizada (o usar existente)
                config, created = ConfiguracionFinanciera.objects.get_or_create(
                    propiedad=propiedad_persona.propiedad,
                    defaults={
                        'nombre': f"Configuración Personalizada - {propiedad_persona.persona}",
                        'es_personalizada': True,
                        'complejo': propiedad_persona.propiedad.complejo,
                        'dia_corte': dia_corte or 1,
                        'dias_vencimiento': dias_venc or 0,
                        'tasa_interes_mora_diaria': tasa_mora or 0,
                        'bloquear_servicios_con_deuda': False
                    }
                )
                
                if not created:
                    # Update existing config with new values
                    config.nombre = f"Configuración Personalizada - {propiedad_persona.persona}"
                    config.es_personalizada = True
                    config.complejo = propiedad_persona.propiedad.complejo # Ensure complex match
                    if dia_corte: config.dia_corte = dia_corte
                    if dias_venc: config.dias_vencimiento = dias_venc
                    if tasa_mora: config.tasa_interes_mora_diaria = tasa_mora
                    config.save()
                cf.configuracion = config
                cf.save()
            
            return propiedad_persona

class EditarContratoForm(forms.ModelForm):
    # Campos de configuración financiera personalizada
    configuracion_personalizada = forms.BooleanField(
        required=False, 
        label="Configuración Personalizada",
        help_text="Permite sobrescribir la configuración financiera global del complejo."
    )
    finanzas_dia_corte = forms.IntegerField(
        min_value=1, max_value=28, required=False, 
        label="Día de Corte",
        help_text="Día del mes para el corte."
    )
    finanzas_dias_vencimiento = forms.IntegerField(
        min_value=0, required=False, 
        label="Días Vencimiento",
        help_text="Días después del corte antes de morosidad."
    )
    finanzas_tasa_mora = forms.DecimalField(
        max_digits=5, decimal_places=3, required=False, 
        label="Tasa Mora Diaria (%)",
        help_text="Porcentaje de interés por día de retraso.",
        widget=forms.NumberInput(attrs={'step': '0.001'})
    )
    finanzas_bloqueo = forms.BooleanField(
        required=False,
        label="Bloquear Servicios con Deuda",
        help_text="Si se marcan, se bloquearán reservas si hay deuda."
    )

    class Meta:
        model = PropiedadPersona
        fields = ['fecha_fin', 'estado']
        widgets = {
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Pre-fill financial config from ContratoFinanciero if exists
        if self.instance.pk:
            try:
                cf = self.instance.contrato_financiero
                if cf and cf.configuracion_personalizada and cf.configuracion:
                    conf = cf.configuracion
                    self.fields['configuracion_personalizada'].initial = True
                    
                    # Only pre-fill override values if they are set on the contract config
                    self.fields['finanzas_dia_corte'].initial = conf.dia_corte
                    self.fields['finanzas_dias_vencimiento'].initial = conf.dias_vencimiento
                    self.fields['finanzas_tasa_mora'].initial = conf.tasa_interes_mora_diaria
                    self.fields['finanzas_bloqueo'].initial = conf.bloquear_servicios_con_deuda
            except Exception:
                pass
            except Exception:
                pass 

        for field_name, field in self.fields.items():
            base_classes = "w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 transition-all text-sm"
            
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = f"{base_classes} appearance-none"
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = "w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500"
            else:
                field.widget.attrs['class'] = base_classes

    def save(self, commit=True):
        instance = super().save(commit=commit)
        
        # Update ContratoFinanciero with overrides
        if instance.pk:
            cf = getattr(instance, 'contrato_financiero', None)
            if cf:
                # Update config flag
                cf.configuracion_personalizada = self.cleaned_data.get('configuracion_personalizada')
                
                if cf.configuracion_personalizada:
                    # Ensure config object exists
                    conf = cf.configuracion
                    if not conf:
                        # Check if one already exists for this property to avoid O2O conflict
                        conf = ConfiguracionFinanciera.objects.filter(propiedad=instance.propiedad).first()
                        
                        if not conf:
                            conf = ConfiguracionFinanciera.objects.create(
                                nombre=f"Configuración Personalizada - {instance.persona}",
                                es_personalizada=True,
                                complejo=instance.propiedad.complejo,
                                propiedad=instance.propiedad
                            )
                        
                        cf.configuracion = conf
                    
                    # Update values
                    conf.dia_corte = self.cleaned_data.get('finanzas_dia_corte') or 1
                    conf.dias_vencimiento = self.cleaned_data.get('finanzas_dias_vencimiento') or 0
                    conf.tasa_interes_mora_diaria = self.cleaned_data.get('finanzas_tasa_mora') or 0
                    conf.bloquear_servicios_con_deuda = self.cleaned_data.get('finanzas_bloqueo')
                    conf.save()
                else:
                    # If customized is false, we keep the object but the contract flag ignores it.
                    pass
                    
                cf.save()
        
        return instance
