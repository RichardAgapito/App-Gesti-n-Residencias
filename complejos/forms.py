from django import forms
from .models import Amenidad, Complejo, Propiedad, PropiedadPersona

class ComplejoForm(forms.ModelForm):
    amenidades = forms.ModelMultipleChoiceField(
        queryset=Amenidad.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Complejo
        fields = '__all__'

class PropiedadForm(forms.ModelForm):
    class Meta:
        model = Propiedad
        exclude = ['numero_identificador', 'residentes', 'tipo', 'complejo']

class CrearPropiedadesMultiplesForm(forms.ModelForm):
    cantidad = forms.IntegerField(min_value=1, label='Cantidad de propiedades a crear')

    class Meta:
        model = Propiedad
        exclude = ['complejo', 'numero_identificador', 'residentes', 'tipo']

class EditarPropiedadForm(forms.ModelForm):
    class Meta:
        model = Propiedad
        fields = ['area', 'numero_habitaciones', 'numero_banos', 'piso_nivel', 'valor_estimado', 'estado_ocupacion']

class PropiedadPersonaForm(forms.ModelForm):
    class Meta:
        model = PropiedadPersona
        fields = ['persona', 'tipo_relacion', 'porcentaje_propiedad', 'fecha_inicio', 'fecha_fin', 'es_principal', 'estado']
