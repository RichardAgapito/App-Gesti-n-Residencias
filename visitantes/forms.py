# visitantes/forms.py
from django import forms
from .models import Visitante
from django.contrib.auth.models import User
from django.utils import timezone # <-- AÑADE ESTA LÍNEA

class VisitanteForm(forms.ModelForm):
    # Usamos 'initial' para poner la fecha de hoy por defecto.
    fecha_visita = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        initial=timezone.now().date() # <-- AÑADE 'initial'
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
        # ... (El resto de la función __init__ se queda exactamente igual) ...
        comunidad = kwargs.pop('comunidad', None)
        super().__init__(*args, **kwargs)

        if comunidad:
            self.fields['residente_visitado'].queryset = User.objects.filter(
                propiedades_habitadas__comunidad=comunidad,
                profile__role='CLIENTE'
            ).distinct()