from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from complejos.models import Complejo

class Persona(models.Model):
    class TipoDocumento(models.TextChoices):
        DNI = 'DNI', 'DNI'
        PASAPORTE = 'PASAPORTE', 'Pasaporte'

    tipo_documento = models.CharField(max_length=10, choices=TipoDocumento.choices)
    numero_documento = models.CharField(max_length=20, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=15)
    fecha_nacimiento = models.DateField()

    def __str__(self):
        return f'{self.nombres} {self.apellidos}'

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        persona_data = extra_fields.pop('persona', None)
        persona = None
        if persona_data:
            if isinstance(persona_data, dict):
                persona = Persona.objects.create(**persona_data)
            elif isinstance(persona_data, Persona):
                persona = persona_data
        
        user = self.model(email=email, persona=persona, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    class Rol(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        GERENTE = 'GERENTE', 'Gerente'
        RESIDENTE = 'RESIDENTE', 'Residente'
        GUARDIA = 'GUARDIA', 'Guardia'

    persona = models.OneToOneField(Persona, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField(unique=True)
    rol = models.CharField(max_length=15, choices=Rol.choices, default=Rol.RESIDENTE)
    complejo_asignado = models.ForeignKey(Complejo, on_delete=models.SET_NULL, null=True, blank=True, related_name='personal_asignado')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)



    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text=
            'The groups this user belongs to. A user will get all permissions ' 
            'granted to each of their groups.',
        related_name="customuser_set",
        related_query_name="customuser",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="customuser_set",
        related_query_name="customuser",
    )

    def __str__(self):
        if self.persona:
            return f'{self.persona.nombres} {self.persona.apellidos}'
        return self.email
