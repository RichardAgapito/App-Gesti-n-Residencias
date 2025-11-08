from django import forms
from .models import Visitante, Visita, PreAutorizacion
from complejos.models import Propiedad, PropiedadPersona
from users.models import CustomUser
from django.utils import timezone


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

    def clean_foto_capturada(self):
        foto = self.cleaned_data.get('foto_capturada', False)
        if not foto:
            raise forms.ValidationError("La foto del visitante es obligatoria.")
        return foto


class VisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        exclude = [
            'usuario_registra', 
            'estado', 
            'fecha_hora_salida', 
            'autorizado_previamente'
        ]
        widgets = {
            'fecha_hora_ingreso': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def __init__(self, *args, **kwargs):
        complejo_asignado = kwargs.pop('complejo_asignado', None)
        self.user = kwargs.pop('user', None)
        super(VisitaForm, self).__init__(*args, **kwargs)

        if complejo_asignado:
            self.fields['propiedad'].queryset = Propiedad.objects.filter(complejo=complejo_asignado)

        # Initially, set the queryset to none.
        self.fields['residente_autoriza'].queryset = CustomUser.objects.none()

        # If the form is bound to data (i.e., it's a POST request)
        if 'propiedad' in self.data:
            try:
                propiedad_id = int(self.data.get('propiedad'))
                # Get all active users (personas) associated with that property
                residentes_ids = PropiedadPersona.objects.filter(
                    propiedad_id=propiedad_id,
                    estado='activo',
                    persona__is_active=True
                ).values_list('persona_id', flat=True)
                # Set the queryset for validation
                self.fields['residente_autoriza'].queryset = CustomUser.objects.filter(id__in=residentes_ids)
            except (ValueError, TypeError):
                pass  # Handle cases where propiedad_id is not a valid number
        # If the form is being initialized with an existing instance (e.g., for editing)
        elif self.instance.pk and self.instance.propiedad:
            residentes_ids = PropiedadPersona.objects.filter(
                propiedad=self.instance.propiedad,
                estado='activo',
                persona__is_active=True
            ).values_list('persona_id', flat=True)
            self.fields['residente_autoriza'].queryset = CustomUser.objects.filter(id__in=residentes_ids)

        self.fields['residente_autoriza'].required = False
        
    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.usuario_registra = self.user
        if commit:
            instance.save()
        return instance

    # (NUEVO) AÑADE ESTE MÉTODO COMPLETO PARA LA VALIDACIÓN
    def clean_visitante(self):
        visitante = self.cleaned_data.get('visitante')
        if not visitante:
            raise forms.ValidationError("Debe seleccionar un visitante registrado.")
        return visitante

    # (NUEVO) AÑADE ESTE MÉTODO COMPLETO
    def clean(self):
        # 1. Obtenemos los datos limpios del formulario
        cleaned_data = super().clean()
        visitante = cleaned_data.get('visitante')

        # 2. Esta validación solo corre al CREAR una visita (cuando self.instance.pk es None)
        #    y solo si el campo 'visitante' fue llenado.
        if self.instance.pk is None and visitante:
            
            # 3. Buscamos si el visitante ya tiene una visita "En Curso"
            #    (Usamos el estado 'en_curso' de tu modelo Visita)
            visita_en_curso_existente = Visita.objects.filter(
                visitante=visitante,
                estado='en_curso'
            ).exists() 

            # 4. Si existe, lanzamos un error de validación
            if visita_en_curso_existente:
                raise forms.ValidationError(
                    f"Error: El visitante '{visitante}' ya tiene una visita 'En Curso'. "
                    "Debe registrar su salida antes de crear una nueva visita."
                )
        
        # 5. Siempre debemos devolver los datos limpios
        return cleaned_data
    
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
