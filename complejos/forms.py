from django import forms
from .models import Amenidad, Complejo, Propiedad, PropiedadPersona
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date, timedelta

class ComplejoForm(forms.ModelForm):
    amenidades = forms.ModelMultipleChoiceField(
        queryset=Amenidad.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Complejo
        fields = '__all__'

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

class PropiedadPersonaForm(forms.ModelForm):
    persona = forms.ModelChoiceField(queryset=get_user_model().objects.filter(rol='RESIDENTE'), label="Persona Principal")
    persona2 = forms.ModelChoiceField(queryset=get_user_model().objects.filter(rol='RESIDENTE'), required=False, label="Segunda Persona")
    porcentaje_propiedad = forms.DecimalField(max_digits=5, decimal_places=2, widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    def __init__(self, *args, **kwargs):
        self.propiedad = kwargs.pop('propiedad', None)
        super().__init__(*args, **kwargs)

    class Meta:
        model = PropiedadPersona
        fields = ['tipo_relacion', 'persona', 'persona2', 'porcentaje_propiedad', 'fecha_inicio', 'fecha_fin', 'estado']
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
                    tipo_relacion='inquilino'
                ).exists():
                    raise ValidationError('Esta persona ya es inquilino de esta propiedad.')
            
            if tipo_relacion == 'inquilino':
                if PropiedadPersona.objects.filter(
                    propiedad=self.propiedad,
                    persona=persona,
                    tipo_relacion__in=['propietario', 'co-propietario']
                ).exists():
                    raise ValidationError('Esta persona ya es propietaria de esta propiedad.')

            if tipo_relacion in ['co-propietario', 'co-inquilino']:
                co_relations = PropiedadPersona.objects.filter(
                    propiedad=self.propiedad,
                    tipo_relacion=tipo_relacion
                )
                if co_relations.count() >= 2:
                    raise ValidationError(f'No se pueden agregar más de 2 {tipo_relacion}s a esta propiedad.')

        return cleaned_data

