from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from .models import Comunidad, Propiedad
from users.views import es_admin 


@user_passes_test(es_admin, login_url='/')
def lista_comunidades(request):
    comunidades = Comunidad.objects.all() 
    context = {
        'comunidades': comunidades
    }
    return render(request, 'comunidades/lista_comunidades.html', context)


@user_passes_test(es_admin, login_url='/')
def crear_comunidad(request):
    pass 


@user_passes_test(es_admin, login_url='/')
def detalle_comunidad(request, comunidad_id):
    comunidad = get_object_or_404(Comunidad, id=comunidad_id)
    
    propiedades_de_la_comunidad = Propiedad.objects.filter(comunidad=comunidad)
    
    context = {
        'comunidad': comunidad,
        'propiedades': propiedades_de_la_comunidad,
    }
    return render(request, 'comunidades/detalle_comunidad.html', context)


@user_passes_test(es_admin, login_url='/')
def crear_propiedad(request, comunidad_id):
    pass