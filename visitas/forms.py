from django import forms
from .models import Visitante, Visita, PreAutorizacion
from complejos.models import Propiedad

class VisitanteForm(forms.ModelForm):
    class Meta:
        model = Visitante
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        tipo_documento = cleaned_data.get('tipo_documento')
        numero_documento = cleaned_data.get('numero_documento')
        nombres = cleaned_data.get('nombres')
        apellidos = cleaned_data.get('apellidos')
        telefono = cleaned_data.get('telefono')

        if nombres and not all(c.isalpha() or c.isspace() for c in nombres):
            self.add_error('nombres', "El nombre solo debe contener letras y espacios.")

        if apellidos and not all(c.isalpha() or c.isspace() for c in apellidos):
            self.add_error('apellidos', "Los apellidos solo deben contener letras y espacios.")

        if telefono:
            if not telefono.isdigit():
                self.add_error('telefono', "El número de teléfono debe contener solo dígitos.")
            elif len(telefono) != 9:
                self.add_error('telefono', "El número de teléfono debe tener exactamente 9 dígitos.")
            elif not telefono.startswith('9'):
                self.add_error('telefono', "El número de teléfono debe comenzar con 9.")

        if tipo_documento and numero_documento:
            if tipo_documento in ['DNI', 'Pasaporte']:
                if not (numero_documento.isdigit() and len(numero_documento) == 8):
                    self.add_error('numero_documento', "Para DNI/Pasaporte, el número de documento debe ser de 8 dígitos numéricos.")
            elif tipo_documento == 'Carnet Extranjeria':
                if not (numero_documento.isdigit() and len(numero_documento) == 9):
                    self.add_error('numero_documento', "Para Carnet de Extranjería, el número de documento debe ser de 9 dígitos numéricos.")
        return cleaned_data

from users.models import CustomUser

from django.utils import timezone

class VisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        exclude = ['usuario_registra']
        widgets = {
            'fecha_hora_ingreso': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control', 'readonly': 'readonly'}),
            'fecha_hora_salida': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        complejo_asignado = kwargs.pop('complejo_asignado', None)
        user = kwargs.pop('user', None)
        super(VisitaForm, self).__init__(*args, **kwargs)
        
        # Initially, the queryset is empty
        self.fields['residente_autoriza'].queryset = CustomUser.objects.none()
        self.fields['residente_autoriza'].required = False

        if complejo_asignado:
            self.fields['propiedad'].queryset = Propiedad.objects.filter(complejo=complejo_asignado)
        
        # If we are processing POST data, we need to populate the queryset
        # for 'residente_autoriza' so that validation can pass.
        if self.is_bound and 'propiedad' in self.data:
            try:
                propiedad_id = int(self.data.get('propiedad'))
                self.fields['residente_autoriza'].queryset = CustomUser.objects.filter(
                    propiedades_asociadas__propiedad_id=propiedad_id,
                    propiedades_asociadas__estado='activo'
                )
            except (ValueError, TypeError):
                pass  # Handle cases where propiedad_id is not a valid number

        # Set initial value for fecha_hora_ingreso to current time
        if not self.instance.pk: # Only for new instances
            self.fields['fecha_hora_ingreso'].initial = timezone.now().strftime('%Y-%m-%dT%H:%M')

    def clean_visitante(self):
        visitante = self.cleaned_data.get('visitante')
        if not visitante:
            raise forms.ValidationError("Debe seleccionar un visitante registrado.")
        return visitante

class EditarVisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        fields = ['fecha_hora_salida']
        widgets = {
            'fecha_hora_salida': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(EditarVisitaForm, self).__init__(*args, **kwargs)
        self.fields['fecha_hora_salida'].required = True

class PreAutorizacionForm(forms.ModelForm):
    class Meta:
        model = PreAutorizacion
        fields = '__all__'
