from django.contrib import admin
from .models import Comunidad, Propiedad


class PropiedadAdmin(admin.ModelAdmin):
    list_display = ('numero_identificador', 'comunidad', 'residente_actual', 'tipo_contrato')
    list_filter = ('comunidad', 'tipo_contrato')
    search_fields = ('numero_identificador', 'residente_actual__username')

admin.site.register(Comunidad)
admin.site.register(Propiedad, PropiedadAdmin)