from django import forms
from .models import Amenidad, Complejo, Propiedad

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
        fields = '__all__'
