from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import JsonResponse
from .models import Complejo, Propiedad, PropiedadPersona, Amenidad, Reserva
from .forms import ComplejoForm, PropiedadForm, CrearPropiedadesMultiplesForm, EditarPropiedadForm, PropiedadPersonaForm, GlobalContratoForm, ReservaForm, AmenidadForm, AdminReservaForm, BloquearHorarioForm, EditarContratoForm
from users.views import es_admin
from django.contrib.auth import get_user_model
from users.models import CustomUser
from django.db import models, transaction
from django.utils import timezone
from collections import defaultdict


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
    
    # Fetch only active contracts
    contratos_activos = propiedad.personas_asociadas.filter(estado='activo').order_by('-fecha_inicio')

    context = {
        'propiedad': propiedad,
        'contratos_activos': contratos_activos,
    }
    return render(request, 'complejos/detalle_propiedad.html', context)


@user_passes_test(es_admin, login_url='/')
def asignar_contrato(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    if request.method == 'POST':
        form = PropiedadPersonaForm(request.POST, propiedad=propiedad)
        if form.is_valid():
            # Determine the actual tipo_relacion for the first person
            tipo_relacion_form = form.cleaned_data['tipo_relacion']
            if tipo_relacion_form == 'co-propietario':
                first_person_role = 'propietario'
                second_person_role = 'co-propietario'
            elif tipo_relacion_form == 'co-inquilino':
                first_person_role = 'inquilino'
                second_person_role = 'co-inquilino'
            else:
                # For single propietario or inquilino, roles are as submitted
                first_person_role = tipo_relacion_form
                second_person_role = None # No second person

            # Create the first PropiedadPersona object
            propiedad_persona = PropiedadPersona(
                propiedad=propiedad,
                persona=form.cleaned_data['persona'],
                tipo_relacion=first_person_role,
                porcentaje_propiedad=form.cleaned_data['porcentaje_propiedad'],
                fecha_inicio=form.cleaned_data['fecha_inicio'],
                fecha_fin=form.cleaned_data['fecha_fin'],
                es_principal=True, # The first person is always principal
                estado=form.cleaned_data['estado']
            )
            propiedad_persona.save()

            # If it's a 'co-' relationship, create the second PropiedadPersona object
            if second_person_role:
                asignacion2 = PropiedadPersona(
                    propiedad=propiedad,
                    persona=form.cleaned_data['persona2'],
                    tipo_relacion=second_person_role,
                    porcentaje_propiedad=form.cleaned_data['porcentaje_propiedad'],
                    fecha_inicio=form.cleaned_data['fecha_inicio'],
                    fecha_fin=form.cleaned_data['fecha_fin'],
                    es_principal=False,
                    estado=form.cleaned_data['estado']
                )
                asignacion2.save()

            return redirect('detalle_propiedad', propiedad_id=propiedad.id)
    else:
        form = PropiedadPersonaForm(propiedad=propiedad)
    return render(request, 'complejos/asignar_contrato.html', {'form': form, 'propiedad': propiedad})


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
@transaction.atomic
def cancelar_contrato(request, propiedad_id, propiedad_persona_id):
    contrato_a_cancelar = get_object_or_404(PropiedadPersona, id=propiedad_persona_id)
    
    # Find partner contract
    partner_contract = PropiedadPersona.objects.filter(
        propiedad_id=propiedad_id,
        fecha_inicio=contrato_a_cancelar.fecha_inicio,
        estado='activo'
    ).exclude(id=propiedad_persona_id).first()

    contrato_a_cancelar.estado = 'inactivo'
    contrato_a_cancelar.save()

    # If a partner exists and we are canceling the main one, promote the partner
    if partner_contract and contrato_a_cancelar.es_principal:
        if partner_contract.tipo_relacion == 'co-propietario':
            partner_contract.tipo_relacion = 'propietario'
        elif partner_contract.tipo_relacion == 'co-inquilino':
            partner_contract.tipo_relacion = 'inquilino'
        
        partner_contract.es_principal = True
        partner_contract.save()
        
    return redirect('lista_contratos')

@user_passes_test(es_admin, login_url='/')
def editar_contrato(request, contrato_id):
    contrato = get_object_or_404(PropiedadPersona, id=contrato_id)
    if request.method == 'POST':
        form = EditarContratoForm(request.POST, instance=contrato)
        if form.is_valid():
            form.save()
            return redirect('detalle_propiedad', propiedad_id=contrato.propiedad.id)
    else:
        form = EditarContratoForm(instance=contrato)
    
    context = {
        'form': form,
    }
    return render(request, 'complejos/editar_contrato.html', context)

@user_passes_test(es_admin, login_url='/')
def reactivar_contrato(request, contrato_id):
    contrato = get_object_or_404(PropiedadPersona, id=contrato_id)
    contrato.estado = 'activo'
    contrato.save()
    return redirect('lista_contratos')

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

@user_passes_test(es_admin, login_url='/')
def lista_contratos(request):
    contratos_qs = PropiedadPersona.objects.select_related(
        'propiedad__complejo', 
        'persona__persona'
    ).order_by('propiedad__numero_identificador', '-fecha_inicio')

    # Filtering
    tipo_relacion = request.GET.get('tipo_relacion', '')
    estado = request.GET.get('estado', '')
    propiedad_id = request.GET.get('propiedad_id', '')

    if tipo_relacion:
        contratos_qs = contratos_qs.filter(tipo_relacion=tipo_relacion)
    
    if estado:
        contratos_qs = contratos_qs.filter(estado=estado)
    
    if propiedad_id:
        contratos_qs = contratos_qs.filter(propiedad__id=propiedad_id)

    # Group contracts by property
    contratos_por_propiedad = defaultdict(list)
    for contrato in contratos_qs:
        contratos_por_propiedad[contrato.propiedad].append(contrato)

    context = {
        'contratos_por_propiedad': dict(contratos_por_propiedad),
        'tipo_relacion_choices': PropiedadPersona.TIPO_RELACION_CHOICES,
        'estado_choices': PropiedadPersona.ESTADO_CHOICES,
        'current_tipo_relacion': tipo_relacion,
        'current_estado': estado,
    }
    return render(request, 'complejos/lista_contratos.html', context)

@user_passes_test(es_admin, login_url='/')
def crear_contrato_global(request):
    if request.method == 'POST':
        form = GlobalContratoForm(request.POST)
        if form.is_valid():
            propiedad = form.cleaned_data['propiedad']
            tipo_relacion_form = form.cleaned_data['tipo_relacion']
            
            if tipo_relacion_form == 'co-propietario':
                first_person_role = 'propietario'
                second_person_role = 'co-propietario'
            elif tipo_relacion_form == 'co-inquilino':
                first_person_role = 'inquilino'
                second_person_role = 'co-inquilino'
            else:
                first_person_role = tipo_relacion_form
                second_person_role = None

            propiedad_persona = PropiedadPersona(
                propiedad=propiedad,
                persona=form.cleaned_data['persona'],
                tipo_relacion=first_person_role,
                fecha_inicio=form.cleaned_data['fecha_inicio'],
                fecha_fin=form.cleaned_data['fecha_fin'],
                es_principal=True,
                estado=form.cleaned_data['estado']
            )
            propiedad_persona.save()

            if second_person_role:
                asignacion2 = PropiedadPersona(
                    propiedad=propiedad,
                    persona=form.cleaned_data['persona2'],
                    tipo_relacion=second_person_role,
                    fecha_inicio=form.cleaned_data['fecha_inicio'],
                    fecha_fin=form.cleaned_data['fecha_fin'],
                    es_principal=False,
                    estado=form.cleaned_data['estado']
                )
                asignacion2.save()
            
            return redirect('lista_contratos')
    else:
        form = GlobalContratoForm()
    
    context = {
        'form': form,
    }
    return render(request, 'complejos/crear_contrato_global.html', context)
