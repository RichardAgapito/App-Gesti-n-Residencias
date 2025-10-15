# users/models.py
from django.db import models
from django.contrib.auth.models import User
from comunidades.models import Comunidad # <-- IMPORTANTE: Añade esta línea

class Profile(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        CLIENTE = 'CLIENTE', 'Cliente'
        PORTERO = 'PORTERO', 'Portero'

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=15, choices=Role.choices, default=Role.CLIENTE)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    # --- NUEVO CAMPO PARA LA ASIGNACIÓN ---
    # Creamos una conexión (ForeignKey) con el modelo Comunidad.
    comunidad_asignada = models.ForeignKey(
        Comunidad, 
        on_delete=models.SET_NULL, # Si se borra la comunidad, el portero no se borra, solo se desasigna.
        null=True, # Puede estar vacío en la base de datos.
        blank=True, # Puede estar vacío en los formularios.
        help_text="Comunidad a la que está asignado el portero."
    )

    def __str__(self):
        return f'{self.user.username} - {self.get_role_display()}'