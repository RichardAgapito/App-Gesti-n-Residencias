from django import forms
from .models import Visitante, Visita, PreAutorizacion

class VisitanteForm(forms.ModelForm):
    class Meta:
        model = Visitante
        fields = '__all__'

class VisitaForm(forms.ModelForm):
    class Meta:
        model = Visita
        fields = '__all__'

class PreAutorizacionForm(forms.ModelForm):
    class Meta:
        model = PreAutorizacion
        fields = '__all__'
