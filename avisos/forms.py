from django import forms
from .models import Aviso, Complejo

class AvisoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and not user.is_staff:
            # Si el usuario no es staff, no puede elegir el complejo.
            # Se asignará automáticamente en la vista.
            if 'complejo' in self.fields:
                del self.fields['complejo']

    class Meta:
        model = Aviso
        fields = ['titulo', 'contenido', 'tipo_aviso', 'dirigido_a', 'complejo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control'}),
            'contenido': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'tipo_aviso': forms.Select(attrs={'class': 'form-control'}),
            'dirigido_a': forms.Select(attrs={'class': 'form-control'}),
            'complejo': forms.Select(attrs={'class': 'form-control'}),
        }
