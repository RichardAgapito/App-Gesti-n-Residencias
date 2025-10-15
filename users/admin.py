# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile

# Define un 'inline' para el modelo Profile.
# Esto permite editar el Profile directamente desde la página del User.
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'perfiles'

# Define una nueva clase de admin para el modelo User
class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

# Vuelve a registrar el modelo User con nuestro UserAdmin personalizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)