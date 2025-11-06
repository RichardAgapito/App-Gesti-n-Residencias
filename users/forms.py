from django import forms
from .models import CustomUser, Persona
from complejos.models import Complejo

class CustomUserCreationForm(forms.ModelForm):
    tipo_documento = forms.ChoiceField(choices=Persona.TipoDocumento.choices)
    numero_documento = forms.CharField(max_length=20)
    nombres = forms.CharField(max_length=100)
    apellidos = forms.CharField(max_length=100)
    telefono = forms.CharField(max_length=15)
    fecha_nacimiento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    rol = forms.ChoiceField(choices=CustomUser.Rol.choices)
    complejo_asignado = forms.ModelChoiceField(queryset=Complejo.objects.all(), required=False)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'rol', 'complejo_asignado']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['complejo_asignado'].widget.attrs['style'] = 'display:none;'

    def clean(self):
        cleaned_data = super().clean()
        rol = cleaned_data.get('rol')
        complejo_asignado = cleaned_data.get('complejo_asignado')

        if rol == CustomUser.Rol.GUARDIA and not complejo_asignado:
            self.add_error('complejo_asignado', 'Este campo es obligatorio para los guardias.')

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