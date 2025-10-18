from django import forms
from .models import Visitante
from django.contrib.auth.models import User
from django.utils import timezone 

class VisitanteForm(forms.ModelForm):
    fecha_visita = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date()
    )
    hora_entrada = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}))
    hora_salida = forms.TimeField(widget=forms.TimeInput(attrs={'type': 'time'}), required=False)

    class Meta:
        model = Visitante
        fields = [
            'tipo_documento', 'numero_documento', 'nombres', 'apellidos',
            'residente_visitado', 'fecha_visita', 'hora_entrada', 'hora_salida'
        ]
        
    def __init__(self, *args, **kwargs):
        comunidad = kwargs.pop('comunidad', None)
        super().__init__(*args, **kwargs)

        if comunidad:
            self.fields['residente_visitado'].queryset = User.objects.filter(
                propiedades_habitadas__comunidad=comunidad,
                profile__role='CLIENTE'
            ).distinct()