from django import forms
from .models import CustomUser, Persona
from complejos.models import Complejo
from django.core.validators import MinLengthValidator, MaxLengthValidator, RegexValidator
from django.utils import timezone
from visitas.models import PreAutorizacion
from django.core.validators import RegexValidator
from datetime import date

class EditarUsuarioForm(forms.ModelForm):
    tipo_documento = forms.ChoiceField(choices=Persona.TipoDocumento.choices, required=True)
    numero_documento = forms.CharField(
        max_length=8,
        validators=[
            RegexValidator(
                r'^\d{8}$',
                message="El número de documento debe contener 8 dígitos."
            )
        ],
        required=True
    )
    nombres = forms.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message="El nombre solo debe contener letras y espacios."
            )
        ],
        required=True
    )
    apellidos = forms.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message="Los apellidos solo deben contener letras y espacios."
            )
        ],
        required=True
    )
    telefono = forms.CharField(
        max_length=9,
        validators=[
            RegexValidator(
                r'^9\d{8}$',
                message="Número de telefono inválido."
            )
        ],
        required=True
    )
    is_active = forms.BooleanField(required=False, label='Activo')

    class Meta:
        model = Persona
        fields = ['tipo_documento', 'numero_documento', 'nombres', 'apellidos', 'telefono']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['is_active'].initial = user.is_active

class CustomUserCreationForm(forms.ModelForm):
    tipo_documento = forms.ChoiceField(choices=Persona.TipoDocumento.choices)
    numero_documento = forms.CharField(
        max_length=8,
        validators=[
            RegexValidator(
                r'^\d{8}$',
                message="El número de documento debe contener 8 dígitos."
            )
        ]
    )
    nombres = forms.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message="El nombre solo debe contener letras y espacios."
            )
        ]
    )
    apellidos = forms.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
                message="Los apellidos solo deben contener letras y espacios."
            )
        ]
    )
    telefono = forms.CharField(
        max_length=9,
        validators=[
            RegexValidator(
                r'^9\d{8}$',
                message="Número de telefono inválido."
            )
        ]
    )
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    email = forms.EmailField()
    password = forms.CharField(
        widget=forms.PasswordInput,
        validators=[
            MinLengthValidator(8, message="La contraseña debe tener al menos 8 caracteres."),
            MaxLengthValidator(20, message="La contraseña no puede tener más de 20 caracteres.")
        ]
    )
    rol = forms.ChoiceField(choices=CustomUser.Rol.choices)
    complejo_asignado = forms.ModelChoiceField(queryset=Complejo.objects.all(), required=False)

    class Meta:
        model = CustomUser
        fields = [
            'tipo_documento',
            'numero_documento',
            'nombres',
            'apellidos',
            'telefono',
            'fecha_nacimiento',
            'email',
            'password',
            'rol',
            'complejo_asignado',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get('rol')
        complejo_asignado = cleaned_data.get('complejo_asignado')
        fecha_nacimiento = cleaned_data.get('fecha_nacimiento')
        numero_documento = cleaned_data.get('numero_documento')

        if Persona.objects.filter(numero_documento=numero_documento).exists():
            self.add_error('numero_documento', 'Ya existe una persona con este número de documento.')

        if rol in [CustomUser.Rol.GUARDIA, CustomUser.Rol.GERENTE]:
            if not complejo_asignado:
                self.add_error('complejo_asignado', f'Este campo es obligatorio para el rol {rol}.')
            
            if rol == CustomUser.Rol.GUARDIA:
                existing_guards = CustomUser.objects.filter(
                    rol=CustomUser.Rol.GUARDIA,
                    complejo_asignado=complejo_asignado
                )
                if self.instance and self.instance.pk:
                    existing_guards = existing_guards.exclude(pk=self.instance.pk)

                if existing_guards.exists():
                    self.add_error('complejo_asignado', 'Este complejo ya tiene un guardia asignado.')
            
            if rol == CustomUser.Rol.GERENTE:
                existing_manager = CustomUser.objects.filter(
                    rol=CustomUser.Rol.GERENTE,
                    complejo_asignado=complejo_asignado
                )
                if self.instance and self.instance.pk:
                    existing_manager = existing_manager.exclude(pk=self.instance.pk)
                
                if existing_manager.exists():
                    self.add_error('complejo_asignado', 'Este complejo ya tiene un gerente asignado.')


        if fecha_nacimiento:
            today = date.today()
            age = today.year - fecha_nacimiento.year - ((today.month, today.day) < (fecha_nacimiento.month, fecha_nacimiento.day))
            if age < 18:
                self.add_error('fecha_nacimiento', 'El usuario debe tener al menos 18 años para registrarse.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            persona = Persona.objects.create(
                tipo_documento=self.cleaned_data['tipo_documento'],
                numero_documento=self.cleaned_data['numero_documento'],
                nombres=self.cleaned_data['nombres'],
                apellidos=self.cleaned_data['apellidos'],
                telefono=self.cleaned_data['telefono'],
                fecha_nacimiento=self.cleaned_data['fecha_nacimiento'],
            )
            user.persona = persona
            user.save()
        return user
    
class ResidentePreAutorizacionForm(forms.ModelForm):

    numero_documento = forms.CharField(
        label="Documento del Visitante",
        validators=[
            RegexValidator(
                r'^\d{8}$',
                message="El número de documento debe contener 8 dígitos."
            )
        ]
    )

    class Meta:
        model = PreAutorizacion

        fields = [
            'nombre_visitante', 
            'numero_documento',
            'fecha_hora_esperada', 
            'vigencia_desde', 
            'vigencia_hasta',
        ]

        exclude = [
            'residente', 
            'propiedad', 
            'estado', 
            'usado', 
            'fecha_uso', 
            'es_recurrente', 
            'dias_semana'
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
        

        cleaned_data['documento_visitante'] = cleaned_data.get('numero_documento')
        return cleaned_data
