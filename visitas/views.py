from django.shortcuts import render, redirect, get_object_or_404
from .models import Visitante, Visita, PreAutorizacion
from .forms import VisitanteForm, VisitaForm, PreAutorizacionForm

def dashboard(request):
    return render(request, 'visitas/dashboard.html')

# Visitante Views
def lista_visitantes_view(request):
    visitantes = Visitante.objects.all()
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

from django.shortcuts import render, redirect, get_object_or_404
from .models import Visitante, Visita, PreAutorizacion
from .forms import VisitanteForm, VisitaForm, PreAutorizacionForm

def dashboard(request):
    return render(request, 'visitas/dashboard.html')

# Visitante Views
# ... (existing views)

# Visita Views
def lista_visitas_view(request):
    visitas = Visita.objects.all()
    context = {
        'visitas': visitas,
    }
    return render(request, 'visitas/lista_visitas.html', context)

def crear_visita_view(request):
    if request.method == 'POST':
        form = VisitaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_visitas')
    else:
        form = VisitaForm()
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
# ... (existing views)

from django.shortcuts import render, redirect, get_object_or_404

from .models import Visitante, Visita, PreAutorizacion

from .forms import VisitanteForm, VisitaForm, PreAutorizacionForm



def dashboard(request):

    return render(request, 'visitas/dashboard.html')



# Visitante Views

# ... (existing views)



# Visita Views

# ... (existing views)



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
