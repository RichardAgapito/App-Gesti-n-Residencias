from django.contrib import admin
from .models import Complejo, Propiedad, PropiedadPersona, Amenidad, Reserva


class PropiedadAdmin(admin.ModelAdmin):
    list_display = ('numero_identificador', 'complejo', 'tipo', 'estado_ocupacion')
    list_filter = ('complejo', 'tipo', 'estado_ocupacion')
    search_fields = ('numero_identificador',)

class ReservaAdmin(admin.ModelAdmin):
    list_display = ('amenidad', 'residente', 'fecha_inicio', 'fecha_fin', 'estado')
    list_filter = ('amenidad', 'estado')
    search_fields = ('residente__email', 'amenidad__nombre')

admin.site.register(Complejo)
admin.site.register(Propiedad, PropiedadAdmin)
admin.site.register(PropiedadPersona)
admin.site.register(Amenidad)
admin.site.register(Reserva, ReservaAdmin)