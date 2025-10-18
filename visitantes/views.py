
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .models import Visitante
from .forms import VisitanteForm


def es_portero(user):
    """
    Verifica si el usuario está autenticado y tiene el rol de 'PORTERO'.
    """
    return user.is_authenticated and user.profile.role == 'PORTERO'


@login_required
@user_passes_test(es_portero, login_url='/')
def lista_visitantes(request):
    """
    Muestra los 5 visitantes más recientes de la comunidad del portero.
    """
    comunidad_portero = request.user.profile.comunidad_asignada
    
    visitantes_recientes = Visitante.objects.filter(
        comunidad=comunidad_portero
    ).order_by('-fecha_visita', '-hora_entrada')[:5]

    context = {
        'visitantes': visitantes_recientes,
    }
    return render(request, 'visitantes/lista_visitantes.html', context)


@login_required
@user_passes_test(es_portero, login_url='/')
def historial_visitantes(request):
    """
    Muestra el historial completo de visitantes y aplica filtros de fecha si se envían.
    """
    comunidad_portero = request.user.profile.comunidad_asignada
    
    historial_qs = Visitante.objects.filter(
        comunidad=comunidad_portero
    ).order_by('-fecha_visita', '-hora_entrada')

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if fecha_inicio and fecha_fin:
        historial_qs = historial_qs.filter(fecha_visita__range=[fecha_inicio, fecha_fin])
        
    context = {
        'historial': historial_qs,
    }
    return render(request, 'visitantes/historial_visitantes.html', context)


@login_required
@user_passes_test(es_portero, login_url='/')
def registrar_visitante(request):
    """
    Maneja la lógica para mostrar y procesar el formulario de registro de un nuevo visitante.
    """
    comunidad_portero = request.user.profile.comunidad_asignada

    if request.method == 'POST':
        form = VisitanteForm(request.POST, comunidad=comunidad_portero)
        if form.is_valid():
            visitante = form.save(commit=False)
            visitante.comunidad = comunidad_portero  
            visitante.save()
            return redirect('lista_visitantes')
    else:
        form = VisitanteForm(comunidad=comunidad_portero)
    
    context = {
        'form': form,
    }
    return render(request, 'visitantes/registrar_visitante.html', context)