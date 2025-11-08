from django import forms
from .models import Amenidad, Complejo, Propiedad, PropiedadPersona, Reserva
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from django.utils import timezone
from visitas.models import PreAutorizacion
from django.core.validators import RegexValidator

# Custom ModelChoiceField to display user's full name
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
            # Primera validación: ¿Contiene solo números?
            if not telefono.isdigit():
                raise ValidationError("Este campo solo debe contener números.")
            # Segunda validación: ¿Tiene la longitud correcta?
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
    porcentaje_propiedad = forms.DecimalField(max_digits=5, decimal_places=2, widget=forms.TextInput(attrs={'readonly': 'readonly'}))

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
        # The persona2 is not part of the model, so we don't need to set an initial value for it
        # when editing. It will be populated from the form data.

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
        fields = ['tipo_relacion', 'porcentaje_propiedad', 'fecha_inicio', 'fecha_fin', 'estado']
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

        # Validations moved from model
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
                    estado='activo' # Only check active contracts
                ).exists():
                    raise ValidationError('Esta persona ya es inquilino activo de esta propiedad.')
            
            if tipo_relacion == 'inquilino':
                if PropiedadPersona.objects.filter(
                    propiedad=self.propiedad,
                    persona=persona,
                    tipo_relacion__in=['propietario', 'co-propietario'],
                    estado='activo' # Only check active contracts
                ).exists():
                    raise ValidationError('Esta persona ya es propietaria activa de esta propiedad.')

            if tipo_relacion in ['co-propietario', 'co-inquilino']:
                co_relations = PropiedadPersona.objects.filter(
                    propiedad=self.propiedad,
                    tipo_relacion=tipo_relacion,
                    estado='activo' # Only check active contracts
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

        # Handle fecha_fin logic
        if tipo_relacion in ['propietario', 'co-propietario']:
            cleaned_data['fecha_fin'] = None
        elif tipo_relacion in ['inquilino', 'co-inquilino']:
            if not fecha_fin:
                self.add_error('fecha_fin', 'La fecha de fin es requerida para los inquilinos.')
            elif fecha_inicio and fecha_fin < fecha_inicio + timedelta(days=30):
                self.add_error('fecha_fin', 'La fecha de fin no puede ser menor a 30 días después de la fecha de inicio.')

        if propiedad and persona:
            # Block creating a new principal if one already exists and is active
            if tipo_relacion in ['propietario', 'co-propietario']:
                if PropiedadPersona.objects.filter(propiedad=propiedad, tipo_relacion='propietario', es_principal=True, estado='activo').exists():
                    raise ValidationError(f"La propiedad '{propiedad}' ya tiene un Propietario principal activo.")
            
            if tipo_relacion in ['inquilino', 'co-inquilino']:
                if PropiedadPersona.objects.filter(propiedad=propiedad, tipo_relacion='inquilino', es_principal=True, estado='activo').exists():
                    raise ValidationError(f"La propiedad '{propiedad}' ya tiene un Inquilino principal activo.")

            # Block assigning a person who is already in an active, conflicting role
            if tipo_relacion in ['propietario', 'co-propietario']:
                if PropiedadPersona.objects.filter(propiedad=propiedad, persona=persona, tipo_relacion='inquilino', estado='activo').exists():
                    raise ValidationError('Esta persona ya es inquilino activo de esta propiedad.')
            
            if tipo_relacion == 'inquilino':
                if PropiedadPersona.objects.filter(propiedad=propiedad, persona=persona, tipo_relacion__in=['propietario', 'co-propietario'], estado='activo').exists():
                    raise ValidationError('Esta persona ya es propietaria activa de esta propiedad.')

        return cleaned_data

class EditarContratoForm(forms.ModelForm):
    class Meta:
        model = PropiedadPersona
        fields = ['fecha_fin', 'estado']
        widgets = {
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

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
            # Check for conflicts with existing reservations
            reservas_en_conflicto = Reserva.objects.filter(
                amenidad=self.amenidad,
                estado__in=['confirmada', 'bloqueada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            ).exists()

            if reservas_en_conflicto:
                raise ValidationError("Este horario ya no está disponible. Por favor, elige otro.")

            # Check if the reservation is within the amenity's operating hours
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
            # Check for conflicts with existing reservations
            reservas_en_conflicto = Reserva.objects.filter(
                amenidad=amenidad,
                estado__in=['confirmada', 'bloqueada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            ).exclude(pk=self.instance.pk)

            if reservas_en_conflicto.exists():
                raise ValidationError("Este horario ya no está disponible. Por favor, elige otro.")

            # Check if the reservation is within the amenity's operating hours
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
            # Check for conflicts with existing reservations
            reservas_en_conflicto = Reserva.objects.filter(
                amenidad=self.amenidad,
                estado__in=['confirmada', 'bloqueada'],
                fecha_inicio__lt=fecha_fin,
                fecha_fin__gt=fecha_inicio
            ).exists()

            if reservas_en_conflicto:
                raise ValidationError("Este horario ya no está disponible. Por favor, elige otro.")

            # Check if the reservation is within the amenity's operating hours
            if fecha_inicio.time() < self.amenidad.hora_inicio:
                raise ValidationError(f"La hora de inicio no puede ser antes de la apertura de la amenidad ({self.amenidad.hora_inicio.strftime('%H:%M')}).")
            
            if fecha_fin.time() > self.amenidad.hora_fin:
                raise ValidationError(f"La hora de fin no puede ser después del cierre de la amenidad ({self.amenidad.hora_fin.strftime('%H:%M')}).")

        return cleaned_data

class ResidentePreAutorizacionForm(forms.ModelForm):
    
    # ... (campo nombre_visitante sin cambios) ...
    nombre_visitante = forms.CharField(
        label="Nombre del Visitante",
        validators=[
            RegexValidator(
                r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message="El nombre solo debe contener letras y espacios."
            )
        ]
    )

    # ... (campo numero_documento sin cambios) ...
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

    # (NUEVO) Campo para "Es recurrente"
    es_recurrente = forms.BooleanField(
        label="¿Es una visita recurrente?",
        required=False # Es opcional
    )
    
    # (NUEVO) Opciones para los días de la semana
    DIAS_CHOICES = (
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado'),
        ('domingo', 'Domingo'),
    )
    
    # (NUEVO) Campo de selección múltiple para los días
    dias_semana = forms.MultipleChoiceField(
        label="Días de la semana recurrentes",
        choices=DIAS_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False # Lo validaremos en el método clean()
    )

    class Meta:
        model = PreAutorizacion
        fields = [
            'nombre_visitante', 
            'numero_documento',
            'fecha_hora_esperada', 
            'vigencia_desde', 
            'vigencia_hasta',
            'es_recurrente', # (NUEVO) Añadido
            'dias_semana',   # (NUEVO) Añadido
        ]
        # (MODIFICADO) Quitamos los campos nuevos de 'exclude'
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
            # (NUEVO) Poblar los campos nuevos si estamos editando
            self.fields['es_recurrente'].initial = self.instance.es_recurrente
            if self.instance.dias_semana:
                # Convertimos el string "lunes,martes" de nuevo a una lista ['lunes', 'martes']
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
        
        # (NUEVO) Asignar los nuevos campos
        instance.es_recurrente = self.cleaned_data.get('es_recurrente')
        
        dias_semana_list = self.cleaned_data.get('dias_semana')
        if dias_semana_list:
            # Convertimos la lista ['lunes', 'viernes'] al string "lunes,viernes"
            # que requiere el modelo
            instance.dias_semana = ",".join(dias_semana_list)
        else:
            instance.dias_semana = "" # Asegurarse de que esté vacío
        
        if commit:
            instance.save()
        return instance
