from django import forms
from .models import Aviso
from complejos.models import Complejo

class AvisoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            if user.is_staff:
                # Si es staff (administrador), puede elegir el complejo
                if user.complejo_asignado:
                    self.fields['complejo'].initial = user.complejo_asignado
                
                # Administradores pueden enviar a TODOS, RESIDENTES o ADMINISTRADORES
                self.fields['dirigido_a'].choices = [
                    (Aviso.DirigidoA.TODOS, 'Todos'),
                    (Aviso.DirigidoA.RESIDENTES, 'Residentes'),
                    (Aviso.DirigidoA.ADMINISTRADORES, 'Administradores'),
                ]
            else:
                # Si es residente, remover completamente el campo complejo del formulario
                if 'complejo' in self.fields:
                    del self.fields['complejo']
                
                # Residentes pueden enviar a TODOS o ADMINISTRADORES
                self.fields['dirigido_a'].choices = [
                    (Aviso.DirigidoA.TODOS, 'Todos'),
                    (Aviso.DirigidoA.ADMINISTRADORES, 'Administradores'),
                ]

    class Meta:
        model = Aviso
        fields = ['titulo', 'contenido', 'tipo_aviso', 'dirigido_a', 'complejo']
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
            'dirigido_a': forms.Select(attrs={'class': 'form-control'}),
            'complejo': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'titulo': 'Título',
            'contenido': 'Contenido',
            'tipo_aviso': 'Tipo de Aviso',
            'dirigido_a': 'Dirigido a',
            'complejo': 'Complejo',
        }
