from django.contrib import admin
from .models import Complejo, Propiedad, PropiedadPersona


class PropiedadAdmin(admin.ModelAdmin):
    list_display = ('numero_identificador', 'complejo', 'tipo', 'estado_ocupacion')
    list_filter = ('complejo', 'tipo', 'estado_ocupacion')
    search_fields = ('numero_identificador',)

admin.site.register(Complejo)
admin.site.register(Propiedad, PropiedadAdmin)
admin.site.register(PropiedadPersona)