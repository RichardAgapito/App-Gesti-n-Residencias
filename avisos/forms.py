from django import forms
from .models import Aviso

class AvisoForm(forms.ModelForm):
    class Meta:
        model = Aviso
        fields = ['titulo', 'contenido', 'tipo_aviso', 'complejo']
        widgets = {
            'titulo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ingrese el título del aviso'
            }),
            'contenido': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5, 
                'placeholder': 'Escriba el contenido del aviso'
            }),
            'tipo_aviso': forms.Select(attrs={'class': 'form-control'}),
            'complejo': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'titulo': 'Título',
            'contenido': 'Contenido',
            'tipo_aviso': 'Tipo de Aviso',
            'complejo': 'Complejo de Destino',
        }
