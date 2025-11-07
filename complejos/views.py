from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import JsonResponse
from .models import Complejo, Propiedad, PropiedadPersona, Amenidad, Reserva
from .forms import ComplejoForm, PropiedadForm, CrearPropiedadesMultiplesForm, EditarPropiedadForm, PropiedadPersonaForm, ReservaForm, AmenidadForm, AdminReservaForm, BloquearHorarioForm
from users.views import es_admin
from django.contrib.auth import get_user_model
from users.models import CustomUser
from django.db import models
from django.utils import timezone


@user_passes_test(es_admin, login_url='/')
def gestionar_amenidades_view(request):
    if request.method == 'POST':
        form = AmenidadForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('gestionar_amenidades')
    else:
        form = AmenidadForm()
    
    amenidades = Amenidad.objects.prefetch_related(
        models.Prefetch('reservas', queryset=Reserva.objects.filter(estado='bloqueada'), to_attr='bloqueos')
    ).all()

    context = {
        'form': form,
        'amenidades': amenidades
    }
    return render(request, 'complejos/gestionar_amenidades.html', context)

@user_passes_test(es_admin, login_url='/')
def editar_amenidad_view(request, amenidad_id):
    amenidad = get_object_or_404(Amenidad, id=amenidad_id)
    if request.method == 'POST':
        form = AmenidadForm(request.POST, instance=amenidad)
        if form.is_valid():
            form.save()
            return redirect('gestionar_amenidades')
    else:
        form = AmenidadForm(instance=amenidad)
    
    context = {
        'form': form,
        'amenidad': amenidad
    }
    return render(request, 'complejos/editar_amenidad.html', context)

@user_passes_test(es_admin, login_url='/')
def eliminar_amenidad_view(request, amenidad_id):
    amenidad = get_object_or_404(Amenidad, id=amenidad_id)
    if request.method == 'POST':
        amenidad.delete()
        return redirect('gestionar_amenidades')
    
    context = {
        'amenidad': amenidad
    }
    return render(request, 'complejos/eliminar_amenidad.html', context)


@user_passes_test(es_admin, login_url='/')
def bloquear_horario_view(request, amenidad_id):
    amenidad = get_object_or_404(Amenidad, id=amenidad_id)
    if request.method == 'POST':
        form = BloquearHorarioForm(request.POST, amenidad=amenidad)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.amenidad = amenidad
            reserva.estado = 'bloqueada'
            reserva.residente = None # A block does not have a resident
            reserva.save()
            return redirect('gestionar_amenidades')
    else:
        form = BloquearHorarioForm(amenidad=amenidad)

    # Fetch existing reservations to display on the calendar
    reservas = Reserva.objects.filter(
        amenidad=amenidad, 
        estado__in=['confirmada', 'bloqueada'], 
        fecha_fin__gt=timezone.now()
    )
    
    context = {
        'form': form,
        'amenidad': amenidad,
        'reservas': reservas, # Pass reservations to the template
    }
    return render(request, 'complejos/bloquear_horario.html', context)


@user_passes_test(es_admin, login_url='/')
def unblock_horario_view(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if reserva.estado == 'bloqueada':
        reserva.delete()
    return redirect('gestionar_amenidades')


@user_passes_test(es_admin, login_url='/')
def lista_complejos(request):
    query = request.GET.get('q')
    tipo = request.GET.get('tipo')
    estado = request.GET.get('estado')

    complejos = Complejo.objects.all()

    if query:
        complejos = complejos.filter(nombre__icontains=query)
    
    if tipo:
        complejos = complejos.filter(tipo=tipo)

    if estado:
        complejos = complejos.filter(estado=estado)

    context = {
        'complejos': complejos,
        'tipo_choices': Complejo.TIPO_CHOICES,
        'estado_choices': Complejo.ESTADO_CHOICES,
        'current_tipo': tipo,
        'current_estado': estado,
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

    query = request.GET.get('q')
    estado = request.GET.get('estado')
    habitaciones = request.GET.get('habitaciones')
    banos = request.GET.get('banos')

    if query:
        propiedades_del_complejo = propiedades_del_complejo.filter(numero_identificador__icontains=query)
    
    if estado:
        propiedades_del_complejo = propiedades_del_complejo.filter(estado_ocupacion=estado)

    if habitaciones:
        propiedades_del_complejo = propiedades_del_complejo.filter(numero_habitaciones=habitaciones)

    if banos:
        propiedades_del_complejo = propiedades_del_complejo.filter(numero_banos=banos)

    context = {
        'complejo': complejo,
        'propiedades': propiedades_del_complejo,
        'query': query,
        'estado_choices': Propiedad.ESTADO_OCUPACION_CHOICES,
        'current_estado': estado,
        'current_habitaciones': habitaciones,
        'current_banos': banos,
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
            propiedad.tipo = 'casa' if complejo.tipo == 'residencial' else 'departamento' # Set tipo here

            # Auto-generate numero_identificador
            last_propiedad = Propiedad.objects.filter(complejo=complejo).order_by('id').last()
            last_id_number = 0
            if last_propiedad:
                try:
                    last_id_number = int(last_propiedad.numero_identificador.split('-')[-1])
                except (ValueError, IndexError):
                    pass # handle cases where the format is not as expected

            prefix = 'D-' if propiedad.tipo == 'departamento' else 'P-'
            propiedad.numero_identificador = f'{prefix}{last_id_number + 1}'
            
            propiedad.save()
            return redirect('detalle_complejo', complejo_id=complejo.id)
    else:
        form = PropiedadForm()
    return render(request, 'complejos/crear_propiedad.html', {'form': form, 'complejo': complejo})

@user_passes_test(es_admin, login_url='/')
def crear_propiedades_multiples(request, complejo_id):
    complejo = get_object_or_404(Complejo, id=complejo_id)
    if request.method == 'POST':
        form = CrearPropiedadesMultiplesForm(request.POST)
        if form.is_valid():
            cantidad = form.cleaned_data['cantidad']
            
            last_propiedad = Propiedad.objects.filter(complejo=complejo).order_by('id').last()
            last_id_number = 0
            if last_propiedad:
                try:
                    last_id_number = int(last_propiedad.numero_identificador.split('-')[-1])
                except (ValueError, IndexError):
                    pass # handle cases where the format is not as expected

            prefix = 'D-' if complejo.tipo == 'condominio' else 'P-' # Use complejo.tipo here

            for i in range(1, cantidad + 1):
                numero_identificador = f'{prefix}{last_id_number + i}'
                propiedad = Propiedad(
                    complejo=complejo,
                    numero_identificador=numero_identificador,
                    tipo='casa' if complejo.tipo == 'residencial' else 'departamento', # Set tipo here
                    area=form.cleaned_data['area'],
                    numero_habitaciones=form.cleaned_data['numero_habitaciones'],
                    numero_banos=form.cleaned_data['numero_banos'],
                    piso_nivel=form.cleaned_data['piso_nivel'],
                    valor_estimado=form.cleaned_data['valor_estimado'],
                    estado_ocupacion=form.cleaned_data['estado_ocupacion']
                )
                propiedad.save()
            return redirect('detalle_complejo', complejo_id=complejo.id)
    else:
        form = CrearPropiedadesMultiplesForm()
    return render(request, 'complejos/crear_propiedades_multiples.html', {'form': form, 'complejo': complejo})

@user_passes_test(es_admin, login_url='/')
def editar_complejo(request, complejo_id):
    complejo = get_object_or_404(Complejo, id=complejo_id)
    if request.method == 'POST':
        form = ComplejoForm(request.POST, instance=complejo)
        if form.is_valid():
            form.save()
            return redirect('detalle_complejo', complejo_id=complejo.id)
    else:
        form = ComplejoForm(instance=complejo)
    return render(request, 'complejos/editar_complejo.html', {'form': form, 'complejo': complejo})

@user_passes_test(es_admin, login_url='/')
def detalle_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    
    # Filter only active PropiedadPersona objects
    personas_asociadas_activas = propiedad.personas_asociadas.filter(estado='activo')
    
    # Check if there are any active contracts
    has_active_contract = personas_asociadas_activas.exists()

    context = {
        'propiedad': propiedad,
        'personas_asociadas_activas': personas_asociadas_activas,
        'has_active_contract': has_active_contract, # Pass the flag to the template
    }
    return render(request, 'complejos/detalle_propiedad.html', context)





@user_passes_test(es_admin, login_url='/')
def editar_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    if request.method == 'POST':
        form = EditarPropiedadForm(request.POST, instance=propiedad)
        if form.is_valid():
            propiedad = form.save(commit=False)
            propiedad.save(skip_validation=True)
            return redirect('detalle_propiedad', propiedad_id=propiedad.id)
    else:
        form = EditarPropiedadForm(instance=propiedad)
    return render(request, 'complejos/editar_propiedad.html', {'form': form, 'propiedad': propiedad})

def get_residentes_json(request):
    residentes = get_user_model().objects.filter(rol='RESIDENTE', is_active=True).values('id', 'persona__nombres', 'persona__apellidos')
    return JsonResponse(list(residentes), safe=False)

@user_passes_test(es_admin, login_url='/')
def cancelar_contrato(request, propiedad_id, propiedad_persona_id):
    propiedad_persona = get_object_or_404(PropiedadPersona, id=propiedad_persona_id)
    
    if propiedad_persona.tipo_relacion in ['co-propietario', 'co-inquilino']:
        # Find all related co-owners/co-tenants for the same property and contract
        co_contratos = PropiedadPersona.objects.filter(
            propiedad_id=propiedad_id,
            tipo_relacion=propiedad_persona.tipo_relacion,
            fecha_inicio=propiedad_persona.fecha_inicio # Assuming fecha_inicio defines a unique contract
        )
        for contrato in co_contratos:
            contrato.estado = 'inactivo'
            contrato.save()
    else:
        propiedad_persona.estado = 'inactivo'
        propiedad_persona.save()
        
    return redirect('detalle_propiedad', propiedad_id=propiedad_id)

def es_residente(user):
    return user.is_authenticated and user.rol == CustomUser.Rol.RESIDENTE

@login_required
@user_passes_test(es_residente)
def crear_reserva_view(request):
    try:
        propiedad_persona = PropiedadPersona.objects.get(persona=request.user, estado='activo')
        complejo = propiedad_persona.propiedad.complejo
        amenidades = complejo.amenidades.prefetch_related(
            models.Prefetch(
                'reservas',
                queryset=Reserva.objects.filter(estado='bloqueada', fecha_fin__gt=timezone.now()),
                to_attr='bloqueos_activos'
            )
        ).all()
    except PropiedadPersona.DoesNotExist:
        complejo = None
        amenidades = []

    # The form is no longer needed for GET requests. 
    # The POST logic will be handled by a different view when we implement the availability calendar.
    if request.method == 'POST':
        # This part is temporarily disabled.
        # The new flow will handle reservations through a dedicated availability view.
        pass

    context = {
        'complejo': complejo,
        'amenidades': amenidades,
    }
    return render(request, 'complejos/crear_reserva.html', context)

@login_required
@user_passes_test(es_residente)
def mis_reservas_view(request):
    reservas = Reserva.objects.filter(residente=request.user).order_by('-fecha_inicio')
    context = {
        'reservas': reservas
    }
    return render(request, 'complejos/mis_reservas.html', context)


@login_required
@user_passes_test(es_residente)
def ver_disponibilidad_view(request, amenidad_id):
    amenidad = get_object_or_404(Amenidad, id=amenidad_id)

    if request.method == 'POST':
        form = ReservaForm(request.POST, amenidad=amenidad)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.amenidad = amenidad
            reserva.residente = request.user
            reserva.save()
            return redirect('mis_reservas')
    else:
        form = ReservaForm(amenidad=amenidad)

    reservas = Reserva.objects.filter(amenidad=amenidad, estado__in=['confirmada', 'bloqueada'], fecha_fin__gt=timezone.now())
    
    context = {
        'amenidad': amenidad,
        'reservas': reservas,
        'form': form,
    }
    return render(request, 'complejos/ver_disponibilidad.html', context)

@user_passes_test(es_admin, login_url='/')
def admin_reservas_view(request):
    reservas = Reserva.objects.all().order_by('-fecha_inicio')

    # Filtering
    complejo_id = request.GET.get('complejo')
    if complejo_id:
        reservas = reservas.filter(amenidad__complejo__id=complejo_id)

    amenidad_id = request.GET.get('amenidad')
    if amenidad_id:
        reservas = reservas.filter(amenidad__id=amenidad_id)

    estado = request.GET.get('estado')
    if estado:
        reservas = reservas.filter(estado=estado)

    context = {
        'reservas': reservas,
        'complejos': Complejo.objects.all(),
        'amenidades': Amenidad.objects.all(),
        'estados': Reserva.ESTADO_CHOICES,
    }
    return render(request, 'complejos/admin_reservas.html', context)

@user_passes_test(es_admin, login_url='/')
def cancelar_reserva_view(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    reserva.estado = 'cancelada'
    reserva.save()
    return redirect('admin_reservas')

@user_passes_test(es_admin, login_url='/')
def admin_crear_reserva(request):
    if request.method == 'POST':
        form = AdminReservaForm(request.POST)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.residente = form.cleaned_data['residente'] # Assign the selected resident
            reserva.save()
            return redirect('admin_reservas')
    else:
        form = AdminReservaForm()
    context = {
        'form': form,
    }
    return render(request, 'complejos/admin_reserva_form.html', context)

@user_passes_test(es_admin, login_url='/')
def admin_editar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if request.method == 'POST':
        form = AdminReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            reserva = form.save(commit=False)
            reserva.residente = form.cleaned_data['residente'] # Assign the selected resident
            reserva.save()
            return redirect('admin_reservas')
    else:
        form = AdminReservaForm(instance=reserva, initial={'residente': reserva.residente})
    context = {
        'form': form,
        'reserva': reserva,
    }
    return render(request, 'complejos/admin_reserva_form.html', context)

@user_passes_test(es_admin, login_url='/')
def approve_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    reserva.estado = 'confirmada'
    reserva.save()
    return redirect('admin_reservas')

@user_passes_test(es_admin, login_url='/')
def reject_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    reserva.estado = 'cancelada'
    reserva.save()
    return redirect('admin_reservas')
