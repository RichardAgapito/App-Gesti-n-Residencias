from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from complejos.models import PropiedadPersona
from django.db import models

def get_residentes_por_propiedad(request, propiedad_id):
    residentes = PropiedadPersona.objects.filter(
        propiedad_id=propiedad_id, 
        estado='activo'
    ).select_related('persona', 'persona__persona')
    
    residentes_data = [
        {
            'id': pp.persona.id, 
            'nombre': f"{pp.persona.persona.nombres} {pp.persona.persona.apellidos}"
        } 
        for pp in residentes if pp.persona and pp.persona.persona
    ]
    
    return JsonResponse(residentes_data, safe=False)

from .models import Visitante, Visita, PreAutorizacion
from .forms import VisitanteForm, VisitaForm, PreAutorizacionForm

def dashboard(request):
    visitantes_dentro = Visita.objects.filter(estado='dentro').count()
    autorizaciones_pendientes = PreAutorizacion.objects.filter(estado='pendiente').count()

    context = {
        'visitantes_dentro': visitantes_dentro,
        'autorizaciones_pendientes': autorizaciones_pendientes,
    }
    return render(request, 'visitas/dashboard.html', context)

# Visitante Views
def lista_visitantes_view(request):
    visitantes = Visitante.objects.all()

    query = request.GET.get('q')
    estado_filter = request.GET.get('estado')

    if query:
        visitantes = visitantes.filter(
            models.Q(nombres__icontains=query) |
            models.Q(numero_documento__icontains=query)
        )

    if estado_filter and estado_filter != '':
        visitantes = visitantes.filter(estado=estado_filter)

    context = {
        'visitantes': visitantes,
    }
    return render(request, 'visitas/lista_visitantes.html', context)

def crear_visitante_view(request):
    if request.method == 'POST':
        form = VisitanteForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('lista_visitantes')
    else:
        form = VisitanteForm()
    return render(request, 'visitas/crear_visitante.html', {'form': form})

def detalle_visitante_view(request, visitante_id):
    visitante = get_object_or_404(Visitante, id=visitante_id)
    context = {
        'visitante': visitante
    }
    return render(request, 'visitas/detalle_visitante.html', context)

def editar_visitante_view(request, visitante_id):
    visitante = get_object_or_404(Visitante, id=visitante_id)
    if request.method == 'POST':
        form = VisitanteForm(request.POST, request.FILES, instance=visitante)
        if form.is_valid():
            form.save()
            return redirect('lista_visitantes')
    else:
        form = VisitanteForm(instance=visitante)
    return render(request, 'visitas/editar_visitante.html', {'form': form, 'visitante': visitante})

def eliminar_visitante_view(request, visitante_id):
    visitante = get_object_or_404(Visitante, id=visitante_id)
    if request.method == 'POST':
        visitante.estado = 'bloqueado'
        visitante.save()
        return redirect('lista_visitantes')
    return render(request, 'visitas/confirmar_eliminar_visitante.html', {'visitante': visitante})

# Visita Views
def lista_visitas_view(request):
    visitas = Visita.objects.all()

    query = request.GET.get('q')
    estado_filter = request.GET.get('estado')
    motivo_visita_filter = request.GET.get('motivo_visita')

    if query:
        visitas = visitas.filter(
            models.Q(visitante__nombres__icontains=query) |
            models.Q(visitante__apellidos__icontains=query) |
            models.Q(visitante__numero_documento__icontains=query) |
            models.Q(propiedad__nombre__icontains=query)
        )

    if estado_filter and estado_filter != '':
        visitas = visitas.filter(estado=estado_filter)

    if motivo_visita_filter and motivo_visita_filter != '':
        visitas = visitas.filter(motivo_visita=motivo_visita_filter)

    context = {
        'visitas': visitas,
    }
    return render(request, 'visitas/lista_visitas.html', context)

def crear_visita_view(request):
    user = request.user
    complejo_asignado = None

    if user.is_authenticated and hasattr(user, 'rol') and user.rol == 'GUARDIA':
        complejo_asignado = user.complejo_asignado

    if request.method == 'POST':
        form = VisitaForm(request.POST, complejo_asignado=complejo_asignado)
        if form.is_valid():
            form.save()
            return redirect('lista_visitas')
    else:
        form = VisitaForm(complejo_asignado=complejo_asignado)
    
    return render(request, 'visitas/crear_visita.html', {'form': form})

def detalle_visita_view(request, visita_id):
    visita = get_object_or_404(Visita, id=visita_id)
    context = {
        'visita': visita
    }
    return render(request, 'visitas/detalle_visita.html', context)

def editar_visita_view(request, visita_id):
    visita = get_object_or_404(Visita, id=visita_id)
    if request.method == 'POST':
        form = VisitaForm(request.POST, instance=visita)
        if form.is_valid():
            form.save()
            return redirect('lista_visitas')
    else:
        form = VisitaForm(instance=visita)
    return render(request, 'visitas/editar_visita.html', {'form': form, 'visita': visita})

def eliminar_visita_view(request, visita_id):
    visita = get_object_or_404(Visita, id=visita_id)
    if request.method == 'POST':
        visita.estado = 'salio'
        visita.save()
        return redirect('lista_visitas')
    return render(request, 'visitas/confirmar_eliminar_visita.html', {'visita': visita})

# PreAutorizacion Views
def lista_preautorizaciones_view(request):
    preautorizaciones = PreAutorizacion.objects.all()
    context = {
        'preautorizaciones': preautorizaciones,
    }
    return render(request, 'visitas/lista_preautorizaciones.html', context)

def crear_preautorizacion_view(request):
    if request.method == 'POST':
        form = PreAutorizacionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_preautorizaciones')
    else:
        form = PreAutorizacionForm()
    return render(request, 'visitas/crear_preautorizacion.html', {'form': form})

def detalle_preautorizacion_view(request, preautorizacion_id):
    preautorizacion = get_object_or_404(PreAutorizacion, id=preautorizacion_id)
    context = {
        'preautorizacion': preautorizacion
    }
    return render(request, 'visitas/detalle_preautorizacion.html', context)

def editar_preautorizacion_view(request, preautorizacion_id):
    preautorizacion = get_object_or_404(PreAutorizacion, id=preautorizacion_id)
    if request.method == 'POST':
        form = PreAutorizacionForm(request.POST, instance=preautorizacion)
        if form.is_valid():
            form.save()
            return redirect('lista_preautorizaciones')
    else:
        form = PreAutorizacionForm(instance=preautorizacion)
    return render(request, 'visitas/editar_preautorizacion.html', {'form': form, 'preautorizacion': preautorizacion})

def eliminar_preautorizacion_view(request, preautorizacion_id):
    preautorizacion = get_object_or_404(PreAutorizacion, id=preautorizacion_id)
    if request.method == 'POST':
        preautorizacion.estado = 'cancelado'
        preautorizacion.save()
        return redirect('lista_preautorizaciones')
    return render(request, 'visitas/confirmar_eliminar_preautorizacion.html', {'preautorizacion': preautorizacion})