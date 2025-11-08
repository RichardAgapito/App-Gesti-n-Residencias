from django import forms
from .models import Visitante, Visita, PreAutorizacion
from complejos.models import Propiedad
from users.models import CustomUser

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


class VisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        # (NUEVO) Excluimos los campos que se llenarán automáticamente
        exclude = [
            'usuario_registra', 
            'estado', 
            'fecha_hora_salida', 
            'autorizado_previamente'
        ]
        # (NUEVO) Añadimos widgets para los campos de fecha y hora
        widgets = {
            'fecha_hora_ingreso': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        complejo_asignado = kwargs.pop('complejo_asignado', None)
        self.user = kwargs.pop('user', None) # (NUEVO) Recibimos el usuario (guardia)
        super(VisitaForm, self).__init__(*args, **kwargs)
        
        # Filtramos las propiedades al complejo del guardia
        if complejo_asignado:
            self.fields['propiedad'].queryset = Propiedad.objects.filter(complejo=complejo_asignado)
        
        # Hacemos que el campo de residentes empiece vacío. Se llenará con JS.
        self.fields['residente_autoriza'].queryset = CustomUser.objects.none()
        self.fields['residente_autoriza'].required = False # No es obligatorio
        
    # (NUEVO) Sobrescribimos 'save' para asignar el guardia
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.usuario_registra = self.user
        if commit:
            instance.save()
        return instance

class PreAutorizacionForm(forms.ModelForm):
    class Meta:
        model = PreAutorizacion
        fields = '__all__'
