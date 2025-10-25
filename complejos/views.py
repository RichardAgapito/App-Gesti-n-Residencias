from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from .models import Complejo, Propiedad
from .forms import ComplejoForm, PropiedadForm
from users.views import es_admin


@user_passes_test(es_admin, login_url='/')
def lista_complejos(request):
    complejos = Complejo.objects.all()
    context = {
        'complejos': complejos
    }
    return render(request, 'complejos/lista_complejos.html', context)


@user_passes_test(es_admin, login_url='/')
def crear_complejo(request):
    if request.method == 'POST':
        form = ComplejoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_complejos')
    else:
        form = ComplejoForm()
    return render(request, 'complejos/crear_complejo.html', {'form': form})


@user_passes_test(es_admin, login_url='/')
def detalle_complejo(request, complejo_id):
    complejo = get_object_or_404(Complejo, id=complejo_id)
    
    propiedades_del_complejo = Propiedad.objects.filter(complejo=complejo)
    
    context = {
        'complejo': complejo,
        'propiedades': propiedades_del_complejo,
    }
    return render(request, 'complejos/detalle_complejo.html', context)


@user_passes_test(es_admin, login_url='/')
def crear_propiedad(request, complejo_id):
    complejo = get_object_or_404(Complejo, id=complejo_id)
    if request.method == 'POST':
        form = PropiedadForm(request.POST)
        if form.is_valid():
            propiedad = form.save(commit=False)
            propiedad.complejo = complejo
            propiedad.save()
            return redirect('detalle_complejo', complejo_id=complejo.id)
    else:
        form = PropiedadForm()
    return render(request, 'complejos/crear_propiedad.html', {'form': form, 'complejo': complejo})