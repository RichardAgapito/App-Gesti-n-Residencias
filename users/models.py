# users/models.py
from django.db import models
from django.contrib.auth.models import User
from complejos.models import Complejo 

class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        CLIENTE = 'CLIENTE', 'Cliente'
        PORTERO = 'PORTERO', 'Portero'

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.CLIENTE)
    telefono = models.CharField(max_length=20, blank=True, null=True)

   
    complejo_asignado = models.ForeignKey(
        Complejo, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        help_text="Complejo al que está asignado el portero."
    )

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'