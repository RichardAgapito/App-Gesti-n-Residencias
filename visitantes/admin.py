# visitantes/admin.py
from django.contrib import admin
from .models import Visitante

@admin.register(Visitante)
class VisitanteAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'apellidos', 'residente_visitado', 'comunidad', 'fecha_visita', 'hora_entrada')
    list_filter = ('comunidad', 'fecha_visita')