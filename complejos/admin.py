from django.contrib import admin
from .models import Complejo, Propiedad


class PropiedadAdmin(admin.ModelAdmin):
    list_display = ('numero_identificador', 'complejo', 'residente_actual', 'tipo', 'estado_ocupacion')
    list_filter = ('complejo', 'tipo', 'estado_ocupacion')
    search_fields = ('numero_identificador', 'residente_actual__username')

admin.site.register(Complejo)
admin.site.register(Propiedad, PropiedadAdmin)