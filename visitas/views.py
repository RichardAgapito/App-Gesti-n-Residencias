from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from complejos.models import Propiedad, PropiedadPersona
from django.db import models
from .models import Visitante, Visita, PreAutorizacion
# (MODIFICADO) Quitamos EditarVisitaForm
from .forms import VisitanteForm, VisitaForm, PreAutorizacionForm
from django.db.models import Q 
from django.contrib.auth.decorators import login_required, user_passes_test
from users.models import CustomUser
from django.core.paginator import Paginator
from django.db.models import Case, When, Value

def es_guardia(user):
    return user.is_authenticated and user.rol == CustomUser.Rol.GUARDIA

def get_residentes_por_propiedad(request, propiedad_id):
    residentes = PropiedadPersona.objects.filter(propiedad_id=propiedad_id, estado='activo').select_related('persona__persona')
    residentes_data = [
        {'id': pp.persona.id, 'nombre': f"{pp.persona.persona.nombres} {pp.persona.persona.apellidos}"} 
        for pp in residentes if pp.persona.persona
    ]
    return JsonResponse(residentes_data, safe=False)

@login_required
@user_passes_test(es_guardia)
def dashboard(request):
    visitantes_dentro = Visita.objects.filter(estado='dentro').count()
    autorizaciones_pendientes = PreAutorizacion.objects.filter(estado='pendiente').count()
    context = {
        'visitantes_dentro': visitantes_dentro,
        'autorizaciones_pendientes': autorizaciones_pendientes,
    }
    return render(request, 'visitas/dashboard.html', context)

# --- Vistas de Visitante ---
@login_required
@user_passes_test(es_guardia)
def lista_visitantes_view(request):
    visitantes = Visitante.objects.all()
    query = request.GET.get('q')
    estado_filter = request.GET.get('estado')

    if query:
        visitantes = visitantes.filter(
            # (MEJORA) Añadido filtro por apellidos
            Q(nombres__icontains=query) |
            Q(apellidos__icontains=query) |
            Q(numero_documento__icontains=query)
        )
    if estado_filter and estado_filter != '':
        visitantes = visitantes.filter(estado=estado_filter)

    context = {
        'visitantes': visitantes,
    }
    return render(request, 'visitas/lista_visitantes.html', context)

@login_required
@user_passes_test(es_guardia)
def crear_visitante_view(request):
    if request.method == 'POST':
        form = VisitanteForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('lista_visitantes')
    else:
        form = VisitanteForm()
    return render(request, 'visitas/crear_visitante.html', {'form': form})

@login_required
@user_passes_test(es_guardia)
def detalle_visitante_view(request, visitante_id):
    visitante = get_object_or_404(Visitante, id=visitante_id)
    context = { 'visitante': visitante }
    return render(request, 'visitas/detalle_visitante.html', context)

@login_required
@user_passes_test(es_guardia)
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

@login_required
@user_passes_test(es_guardia)
def eliminar_visitante_view(request, visitante_id):
    visitante = get_object_or_404(Visitante, id=visitante_id)
    if request.method == 'POST':
        visitante.estado = 'bloqueado'
        visitante.save()
        return redirect('lista_visitantes')
    return render(request, 'visitas/confirmar_eliminar_visitante.html', {'visitante': visitante})


# --- Vistas de Visita ---
@login_required
@user_passes_test(es_guardia)
def lista_visitas_view(request):
    user = request.user
    visitas_list = Visita.objects.all().order_by('-fecha_hora_ingreso')
    propiedades = Propiedad.objects.all()

    if user.is_authenticated and hasattr(user, 'rol') and user.rol == 'GUARDIA' and user.complejo_asignado:
        visitas_list = visitas_list.filter(propiedad__complejo=user.complejo_asignado)
        propiedades = propiedades.filter(complejo=user.complejo_asignado)

    query = request.GET.get('q')
    estado_filter = request.GET.get('estado')
    propiedad_filter = request.GET.get('propiedad')

    if query:
        visitas_list = visitas_list.filter(
            # (MEJORA) Añadido filtro por apellidos del visitante
            Q(visitante__nombres__icontains=query) |
            Q(visitante__apellidos__icontains=query) |
            Q(visitante__numero_documento__icontains=query) |
            Q(propiedad__numero_identificador__icontains=query)
        )
    if estado_filter and estado_filter != '':
        visitas_list = visitas_list.filter(estado=estado_filter)
    if propiedad_filter and propiedad_filter != '':
        visitas_list = visitas_list.filter(propiedad__id=propiedad_filter)

    paginator = Paginator(visitas_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'estado_choices': Visita.ESTADO_CHOICES,
        'propiedades': propiedades,
    }
    return render(request, 'visitas/lista_visitas.html', context)

@login_required
@user_passes_test(es_guardia)
def crear_visita_view(request):
    user = request.user
    complejo_asignado = None
    if user.is_authenticated and hasattr(user, 'rol') and user.rol == 'GUARDIA':
        complejo_asignado = user.complejo_asignado

    if request.method == 'POST':
        form = VisitaForm(request.POST, complejo_asignado=complejo_asignado, user=user)
        if form.is_valid():
            visita = form.save(commit=False)
            visita.estado = 'dentro'
            visita.save()
            return redirect('lista_visitas')
    else:
        form = VisitaForm(complejo_asignado=complejo_asignado, user=user)
    
    return render(request, 'visitas/crear_visita.html', {'form': form})

@login_required
@user_passes_test(es_guardia)
def detalle_visita_view(request, visita_id):
    visita = get_object_or_404(Visita, id=visita_id)
    context = { 'visita': visita }
    return render(request, 'visitas/detalle_visita.html', context)

# (ELIMINADA) La vista 'editar_visita_view' se ha ido.

# (MODIFICADA) Esta es la nueva 'registrar_salida_visita_view'
@login_required
@user_passes_test(es_guardia)
def registrar_salida_visita_view(request, visita_id):
    visita = get_object_or_404(Visita, id=visita_id)
    if request.method == 'POST':
        visita.estado = 'salio'
        # (NUEVO) Registramos la hora de salida
        visita.fecha_hora_salida = timezone.now() 
        visita.save()
        return redirect('lista_visitas')
    # Usamos la plantilla de confirmación existente
    return render(request, 'visitas/confirmar_eliminar_visita.html', {'visita': visita})


# --- Vistas de PreAutorizacion (solo Guardia) ---
@login_required
@user_passes_test(es_guardia)
def lista_preautorizaciones_view(request):
    
    # (NUEVO) Filtrar por el complejo del guardia
    user = request.user
    guardia_complejo = None
    if user.is_authenticated and hasattr(user, 'rol') and user.rol == 'GUARDIA':
        guardia_complejo = user.complejo_asignado

    # Query base (sin cambios, sigue ordenando por prioridad)
    preautorizaciones_qs = PreAutorizacion.objects.select_related(
        'propiedad__complejo', 'residente__persona'
    ).annotate(
        status_order=Case(
            When(estado='pendiente', then=Value(1)),
            When(estado='usado', then=Value(2)),
            default=Value(3)
        )
    ).order_by('status_order', 'fecha_hora_esperada')

    # (NUEVO) Obtener listas para los dropdowns de filtros
    propiedades_list = Propiedad.objects.all()
    residentes_list = CustomUser.objects.filter(rol='RESIDENTE', is_active=True).select_related('persona')

    # (NUEVO) Aplicar filtro de complejo si el guardia está asignado
    if guardia_complejo:
        preautorizaciones_qs = preautorizaciones_qs.filter(propiedad__complejo=guardia_complejo)
        propiedades_list = propiedades_list.filter(complejo=guardia_complejo)
        residentes_list = residentes_list.filter(propiedades_asociadas__propiedad__complejo=guardia_complejo).distinct()

    # Obtener valores de los filtros
    query = request.GET.get('q')
    estado_filter = request.GET.get('estado')
    propiedad_filter_id = request.GET.get('propiedad') # (NUEVO)
    residente_filter_id = request.GET.get('residente') # (NUEVO)

    # Aplicar filtros
    if query:
        preautorizaciones_qs = preautorizaciones_qs.filter(
            Q(nombre_visitante__icontains=query) |
            Q(documento_visitante__icontains=query) |
            Q(residente__persona__nombres__icontains=query) |
            Q(residente__persona__apellidos__icontains=query)
        )
    if estado_filter:
        preautorizaciones_qs = preautorizaciones_qs.filter(estado=estado_filter)
    
    if propiedad_filter_id: # (NUEVO)
        preautorizaciones_qs = preautorizaciones_qs.filter(propiedad_id=propiedad_filter_id)
    
    if residente_filter_id: # (NUEVO)
        preautorizaciones_qs = preautorizaciones_qs.filter(residente_id=residente_filter_id)

    context = {
        'preautorizaciones': preautorizaciones_qs,
        'estado_choices': PreAutorizacion.ESTADO_CHOICES,
        'propiedades': propiedades_list, # (NUEVO)
        'residentes': residentes_list, # (NUEVO)
        'current_estado': estado_filter,
        'current_propiedad': int(propiedad_filter_id) if propiedad_filter_id else None, # (NUEVO)
        'current_residente': int(residente_filter_id) if residente_filter_id else None, # (NUEVO)
        'query': query,
    }
    return render(request, 'visitas/lista_preautorizaciones.html', context)

@login_required
@user_passes_test(es_guardia)
def aprobar_preautorizacion_view(request, pa_id):
    autorizacion = get_object_or_404(PreAutorizacion, id=pa_id)
    if autorizacion.estado == 'pendiente':
        autorizacion.estado = 'usado' 
        autorizacion.save()
    return redirect('lista_preautorizaciones')

@login_required
@user_passes_test(es_guardia)
def cancelar_preautorizacion_view(request, pa_id):
    autorizacion = get_object_or_404(PreAutorizacion, id=pa_id)
    if autorizacion.estado == 'pendiente':
        autorizacion.estado = 'cancelado'
        autorizacion.save()
    return redirect('lista_preautorizaciones')