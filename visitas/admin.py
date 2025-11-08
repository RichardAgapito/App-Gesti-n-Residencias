from django.contrib import admin
from .models import Visitante, Visita, PreAutorizacion

# (NUEVO) Registramos los modelos para que aparezcan en el panel de admin
admin.site.register(Visitante)
admin.site.register(Visita)
admin.site.register(PreAutorizacion)
