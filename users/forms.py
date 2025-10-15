# users/forms.py (archivo nuevo)
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

# Creamos un formulario que hereda del UserCreationForm de Django
class CustomUserCreationForm(UserCreationForm):
    # Añadimos nuestro campo 'role' del modelo Profile
    role = forms.ChoiceField(choices=Profile.Role.choices)

    class Meta(UserCreationForm.Meta):
        # Añadimos más campos que queremos en el formulario
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email',)