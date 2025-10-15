# comunidades/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from .models import Comunidad, Propiedad
from users.views import es_admin # Importamos la función que verifica si un usuario es admin

# NOTA: Aún no creamos los formularios, así que los comentaremos temporalmente
# from .forms import ComunidadForm, PropiedadForm 

# --- VISTAS ---

# 1. Vista para la LISTA de comunidades
@user_passes_test(es_admin, login_url='/')
def lista_comunidades(request):
    comunidades = Comunidad.objects.all() # Obtenemos todas las comunidades de la BD
    context = {
        'comunidades': comunidades
    }
    return render(request, 'comunidades/lista_comunidades.html', context)


# 2. Vista para CREAR una comunidad (la dejaremos vacía por ahora)
@user_passes_test(es_admin, login_url='/')
def crear_comunidad(request):
    # Lógica del formulario vendrá aquí
    pass 


# 3. Vista para el DETALLE de una comunidad (la dejaremos vacía por ahora)
@user_passes_test(es_admin, login_url='/')
def detalle_comunidad(request, comunidad_id):
    # Busca la comunidad por su ID. Si no la encuentra, muestra un error 404.
    comunidad = get_object_or_404(Comunidad, id=comunidad_id)
    
    # Busca todas las propiedades que pertenecen a ESTA comunidad.
    propiedades_de_la_comunidad = Propiedad.objects.filter(comunidad=comunidad)
    
    context = {
        'comunidad': comunidad,
        'propiedades': propiedades_de_la_comunidad,
    }
    return render(request, 'comunidades/detalle_comunidad.html', context)


# 4. Vista para AÑADIR una propiedad (la dejaremos vacía por ahora)
@user_passes_test(es_admin, login_url='/')
def crear_propiedad(request, comunidad_id):
    # Lógica del formulario vendrá aquí
    pass