from django.contrib import admin
from .models import Aviso

@admin.register(Aviso)
class AvisoAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'autor', 'complejo', 'tipo_aviso', 'dirigido_a', 'fecha_creacion')
    list_filter = ('complejo', 'tipo_aviso', 'dirigido_a')
    search_fields = ('titulo', 'contenido', 'autor__email')
    raw_id_fields = ('autor', 'complejo', 'leido_por')
