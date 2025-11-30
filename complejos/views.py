from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import JsonResponse
from .models import Complejo, Propiedad, PropiedadPersona, Amenidad, Reserva
from finanzas.models import Factura, ConfiguracionFinanciera
from .forms import (
    ComplejoForm, PropiedadForm, CrearPropiedadesMultiplesForm, EditarPropiedadForm, 
    PropiedadPersonaForm, GlobalContratoForm, ReservaForm, AmenidadForm, 
    AdminReservaForm, BloquearHorarioForm, EditarContratoForm, ResidentePreAutorizacionForm
)
from users.views import es_admin
from django.contrib.auth import get_user_model
from users.models import CustomUser
from django.db import models, transaction
from django.utils import timezone
from collections import defaultdict
from visitas.models import PreAutorizacion


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
            reserva.residente = None
            reserva.save()
            return redirect('gestionar_amenidades')
    else:
        form = BloquearHorarioForm(amenidad=amenidad)


    reservas = Reserva.objects.filter(
        amenidad=amenidad, 
        estado__in=['confirmada', 'bloqueada'], 
        fecha_fin__gt=timezone.now()
    )
    
    context = {
        'form': form,
        'amenidad': amenidad,
        'reservas': reservas,
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
    from django.db.models import Count, Q
    
    query = request.GET.get('q')
    tipo = request.GET.get('tipo')
    estado = request.GET.get('estado')

    # 1. Obtener QuerySet con anotaciones
    complejos_qs = Complejo.objects.annotate(
        total_amenidades=Count('amenidades', distinct=True),
        unidades_ocupadas=Count('propiedades', filter=Q(propiedades__estado_ocupacion='ocupado'), distinct=True)
    )

    # 2. Convertir a lista para poder agregar atributos dinámicos (porcentaje)
    complejos_list = list(complejos_qs)

    # 3. Calcular porcentajes en los objetos de la lista
    for c in complejos_list:
        if c.numero_total_unidades > 0:
            c.porcentaje_ocupacion = int((c.unidades_ocupadas / c.numero_total_unidades) * 100)
        else:
            c.porcentaje_ocupacion = 0

    # 4. Filtrar sobre la lista (Python filtering)
    if query:
        query_lower = query.lower()
        complejos_list = [c for c in complejos_list if query_lower in c.nombre.lower() or query_lower in c.calle.lower() or (c.administrador_responsable and query_lower in c.administrador_responsable.lower())]
    
    if tipo:
        complejos_list = [c for c in complejos_list if c.tipo == tipo]

    if estado:
        complejos_list = [c for c in complejos_list if c.estado == estado]

    context = {
        'complejos': complejos_list,
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
            propiedad.tipo = 'casa' if complejo.tipo == 'residencial' else 'departamento'


            last_propiedad = Propiedad.objects.filter(complejo=complejo).order_by('id').last()
            last_id_number = 0
            if last_propiedad:
                try:
                    last_id_number = int(last_propiedad.numero_identificador.split('-')[-1])
                except (ValueError, IndexError):
                    pass

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
                    pass

            prefix = 'D-' if complejo.tipo == 'condominio' else 'P-'

            for i in range(1, cantidad + 1):
                numero_identificador = f'{prefix}{last_id_number + i}'
                propiedad = Propiedad(
                    complejo=complejo,
                    numero_identificador=numero_identificador,
                    tipo='casa' if complejo.tipo == 'residencial' else 'departamento',
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
            next_url = request.POST.get('next')
            if next_url:
                return redirect(next_url)
            return redirect('detalle_complejo', complejo_id=complejo.id)
    else:
        form = ComplejoForm(instance=complejo)
    return render(request, 'complejos/editar_complejo.html', {'form': form, 'complejo': complejo})

@user_passes_test(es_admin, login_url='/')
def detalle_propiedad(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    

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
                porcentaje_propiedad=form.cleaned_data['porcentaje_propiedad'],
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
    

    partner_contract = PropiedadPersona.objects.filter(
        propiedad_id=propiedad_id,
        fecha_inicio=contrato_a_cancelar.fecha_inicio,
        estado='activo'
    ).exclude(id=propiedad_persona_id).first()

    contrato_a_cancelar.estado = 'inactivo'
    contrato_a_cancelar.save()


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
    complejo = None
    amenidades = []
    has_active_contract = False
    
    # Variables nuevas para el bloqueo
    usuario_bloqueado = False
    mensaje_bloqueo = ""

    propiedad_persona = PropiedadPersona.objects.filter(persona=request.user, estado='activo').first()

    if propiedad_persona:
        has_active_contract = True
        complejo = propiedad_persona.propiedad.complejo
        
        # --- LÓGICA DE BLOQUEO FINANCIERO (NUEVA) ---
        # 1. Buscamos la configuración del complejo
        config_fin = getattr(complejo, 'configuracion_financiera', None)
        
        if config_fin and config_fin.bloquear_servicios_con_deuda:
            # 2. Buscamos si tiene facturas VENCIDAS (Deuda exigible)
            facturas_vencidas = Factura.objects.filter(
                propiedad=propiedad_persona.propiedad,
                estado='VENCIDA'
            ).count()
            
            if facturas_vencidas > 0:
                usuario_bloqueado = True
                mensaje_bloqueo = f"Servicio restringido. Tienes {facturas_vencidas} factura(s) vencida(s). Por favor regulariza tu situación en Finanzas."
        # ---------------------------------------------

        if complejo and not usuario_bloqueado: # Solo cargamos amenidades si NO está bloqueado
            amenidades = complejo.amenidades.prefetch_related(
                models.Prefetch(
                    'reservas',
                    queryset=Reserva.objects.filter(estado='bloqueada', fecha_fin__gt=timezone.now()),
                    to_attr='bloqueos_activos'
                )
            ).all()

    # (El resto de tu vista sigue igual, solo pasamos las nuevas variables al contexto)
    context = {
        'complejo': complejo,
        'amenidades': amenidades,
        'has_active_contract': has_active_contract,
        'usuario_bloqueado': usuario_bloqueado, # <--- Nuevo
        'mensaje_bloqueo': mensaje_bloqueo      # <--- Nuevo
    }
    return render(request, 'complejos/crear_reserva.html', context)

@login_required
@user_passes_test(es_residente)
def mis_reservas_view(request):

    has_active_contract = PropiedadPersona.objects.filter(persona=request.user, estado='activo').exists()
    
    reservas = Reserva.objects.filter(residente=request.user).order_by('-fecha_inicio')
    context = {
        'reservas': reservas,
        'has_active_contract': has_active_contract
    }
    return render(request, 'complejos/mis_reservas.html', context)


@login_required
@user_passes_test(es_residente)
def ver_disponibilidad_view(request, amenidad_id):

    has_active_contract = PropiedadPersona.objects.filter(persona=request.user, estado='activo').exists()
    if not has_active_contract:
        return redirect('dashboard')
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
        'has_active_contract': has_active_contract
    }
    return render(request, 'complejos/ver_disponibilidad.html', context)

def es_admin_o_gerente(user):
    return user.is_authenticated and (user.rol == CustomUser.Rol.ADMIN or user.rol == CustomUser.Rol.GERENTE)

@user_passes_test(es_admin_o_gerente, login_url='/')
def admin_reservas_view(request):
    reservas = Reserva.objects.all().order_by('-fecha_inicio')
    complejos = Complejo.objects.all()
    amenidades = Amenidad.objects.all()
    
    # Role-based filtering
    if request.user.rol == CustomUser.Rol.GERENTE:
        if request.user.complejo_asignado:
            # Filter by the new direct ForeignKey 'complejo'
            # Note: This will only show reservations created AFTER this schema change or backfilled ones.
            # Fallback to amenidad__complejo for older records if needed, but user requested this field for filtering.
            # We use Q objects to support both new (direct FK) and old (via amenidad) if we wanted compatibility,
            # but strictly following the request to use the new key:
            reservas = reservas.filter(complejo=request.user.complejo_asignado)
            
            complejos = complejos.filter(id=request.user.complejo_asignado.id)
            amenidades = amenidades.filter(complejo=request.user.complejo_asignado)
        else:
            # Manager without complex sees nothing
            reservas = Reserva.objects.none()
            complejos = Complejo.objects.none()
            amenidades = Amenidad.objects.none()

    complejo_id = request.GET.get('complejo')
    if complejo_id:
        reservas = reservas.filter(complejo__id=complejo_id)

    amenidad_id = request.GET.get('amenidad')
    if amenidad_id:
        reservas = reservas.filter(amenidad__id=amenidad_id)

    estado = request.GET.get('estado')
    if estado:
        reservas = reservas.filter(estado=estado)

    context = {
        'reservas': reservas,
        'complejos': complejos,
        'amenidades': amenidades,
        'estados': Reserva.ESTADO_CHOICES,
    }
    return render(request, 'complejos/admin_reservas.html', context)

@user_passes_test(es_admin_o_gerente, login_url='/')
def cancelar_reserva_view(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    # Ensure Manager can only cancel their own complex's reservations
    if request.user.rol == CustomUser.Rol.GERENTE:
        # Use new complejo field if available, otherwise fallback to amenidad check or just enforce strict check
        if not request.user.complejo_asignado:
             return redirect('admin_reservas')
        
        # Check if reservation belongs to manager's complex (using new field or amenidad relation)
        if reserva.complejo and reserva.complejo != request.user.complejo_asignado:
             return redirect('admin_reservas')
        elif not reserva.complejo and not reserva.amenidad.complejo_set.filter(id=request.user.complejo_asignado.id).exists():
             return redirect('admin_reservas')
            
    reserva.estado = 'cancelada'
    reserva.save()
    return redirect('admin_reservas')

@user_passes_test(es_admin_o_gerente, login_url='/')
def admin_crear_reserva(request):
    # Admins cannot create reservations
    if request.user.rol == CustomUser.Rol.ADMIN:
        return redirect('admin_reservas')
        
    # Managers without complex cannot create reservations
    if request.user.rol == CustomUser.Rol.GERENTE and not request.user.complejo_asignado:
        return redirect('admin_reservas')

    if request.method == 'POST':
        form = AdminReservaForm(request.POST)
        # Filter queryset for validation if Manager
        if request.user.rol == CustomUser.Rol.GERENTE:
             # Use 'complejo' for queryset filtering
             form.fields['amenidad'].queryset = Amenidad.objects.filter(complejo=request.user.complejo_asignado)
             # Filter residents: only those with active property in the complex
             form.fields['residente'].queryset = get_user_model().objects.filter(
                propiedades_asociadas__propiedad__complejo=request.user.complejo_asignado,
                propiedades_asociadas__estado='activo'
             ).distinct()
             
        if form.is_valid():
            reserva = form.save(commit=False)
            # Double check for Manager
            if request.user.rol == CustomUser.Rol.GERENTE:
                # Use complejo_set for instance access
                if not reserva.amenidad.complejo_set.filter(id=request.user.complejo_asignado.id).exists():
                     return redirect('admin_reservas')
                # Populate the new complejo field
                reserva.complejo = request.user.complejo_asignado

            reserva.residente = form.cleaned_data['residente']
            reserva.save()
            return redirect('admin_reservas')
    else:
        form = AdminReservaForm()
        # Filter queryset for display if Manager
        if request.user.rol == CustomUser.Rol.GERENTE:
             # Use 'complejo' for queryset filtering
             form.fields['amenidad'].queryset = Amenidad.objects.filter(complejo=request.user.complejo_asignado)
             # Filter residents: only those with active property in the complex
             form.fields['residente'].queryset = get_user_model().objects.filter(
                propiedades_asociadas__propiedad__complejo=request.user.complejo_asignado,
                propiedades_asociadas__estado='activo'
             ).distinct()

    context = {
        'form': form,
    }
    return render(request, 'complejos/admin_reserva_form.html', context)

@user_passes_test(es_admin_o_gerente, login_url='/')
def admin_editar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    # Check permission for Manager
    if request.user.rol == CustomUser.Rol.GERENTE:
        if not request.user.complejo_asignado:
             return redirect('admin_reservas')
        
        # Check permission using new field or fallback
        if reserva.complejo and reserva.complejo != request.user.complejo_asignado:
            return redirect('admin_reservas')
        elif not reserva.complejo and not reserva.amenidad.complejo_set.filter(id=request.user.complejo_asignado.id).exists():
            return redirect('admin_reservas')

    if request.method == 'POST':
        form = AdminReservaForm(request.POST, instance=reserva)
        # Filter queryset for validation if Manager
        if request.user.rol == CustomUser.Rol.GERENTE:
             # Use 'complejo' for queryset filtering
             form.fields['amenidad'].queryset = Amenidad.objects.filter(complejo=request.user.complejo_asignado)
             form.fields['residente'].queryset = get_user_model().objects.filter(
                propiedades_asociadas__propiedad__complejo=request.user.complejo_asignado,
                propiedades_asociadas__estado='activo'
             ).distinct()

        if form.is_valid():
            reserva = form.save(commit=False)
            # Double check for Manager
            if request.user.rol == CustomUser.Rol.GERENTE:
                if not reserva.amenidad.complejo_set.filter(id=request.user.complejo_asignado.id).exists():
                     return redirect('admin_reservas')
                # Ensure complejo is set if it wasn't
                if not reserva.complejo:
                    reserva.complejo = request.user.complejo_asignado

            reserva.residente = form.cleaned_data['residente']
            reserva.save()
            return redirect('admin_reservas')
    else:
        form = AdminReservaForm(instance=reserva, initial={'residente': reserva.residente})
        # Filter queryset for display if Manager
        if request.user.rol == CustomUser.Rol.GERENTE:
             # Use 'complejo' for queryset filtering
             form.fields['amenidad'].queryset = Amenidad.objects.filter(complejo=request.user.complejo_asignado)
             form.fields['residente'].queryset = get_user_model().objects.filter(
                propiedades_asociadas__propiedad__complejo=request.user.complejo_asignado,
                propiedades_asociadas__estado='activo'
             ).distinct()

    context = {
        'form': form,
        'reserva': reserva,
    }
    return render(request, 'complejos/admin_reserva_form.html', context)

@user_passes_test(es_admin_o_gerente, login_url='/')
def approve_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    # Check permission for Manager
    if request.user.rol == CustomUser.Rol.GERENTE:
        if not request.user.complejo_asignado:
             return redirect('admin_reservas')
        if reserva.complejo and reserva.complejo != request.user.complejo_asignado:
             return redirect('admin_reservas')
        elif not reserva.complejo and not reserva.amenidad.complejo_set.filter(id=request.user.complejo_asignado.id).exists():
             return redirect('admin_reservas')
            
    reserva.estado = 'confirmada'
    reserva.save()
    return redirect('admin_reservas')

@user_passes_test(es_admin_o_gerente, login_url='/')
def reject_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    # Check permission for Manager
    if request.user.rol == CustomUser.Rol.GERENTE:
        if not request.user.complejo_asignado:
             return redirect('admin_reservas')
        if reserva.complejo and reserva.complejo != request.user.complejo_asignado:
             return redirect('admin_reservas')
        elif not reserva.complejo and not reserva.amenidad.complejo_set.filter(id=request.user.complejo_asignado.id).exists():
             return redirect('admin_reservas')
            
    reserva.estado = 'cancelada'
    reserva.save()
    return redirect('admin_reservas')

@user_passes_test(es_admin, login_url='/')
def lista_contratos(request):
    contratos_qs = PropiedadPersona.objects.select_related(
        'propiedad__complejo', 
        'persona__persona'
    ).order_by('propiedad__numero_identificador', '-fecha_inicio')


    tipo_relacion = request.GET.get('tipo_relacion', '')
    estado = request.GET.get('estado', '')
    propiedad_id = request.GET.get('propiedad_id', '')

    if tipo_relacion:
        contratos_qs = contratos_qs.filter(tipo_relacion=tipo_relacion)
    
    if estado:
        contratos_qs = contratos_qs.filter(estado=estado)
    
    if propiedad_id:
        contratos_qs = contratos_qs.filter(propiedad__id=propiedad_id)


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

@login_required
@user_passes_test(es_residente)
def mis_preautorizaciones_view(request):
    has_active_contract = PropiedadPersona.objects.filter(persona=request.user, estado='activo').exists()
    
    lista_autorizaciones = PreAutorizacion.objects.filter(
        residente=request.user
    ).order_by('-fecha_hora_esperada')
    
    context = {
        'has_active_contract': has_active_contract,
        'autorizaciones': lista_autorizaciones
    }
    return render(request, 'complejos/mis_preautorizaciones.html', context)

@login_required
@user_passes_test(es_residente)
def crear_preautorizacion_view(request):
    try:

        propiedad_persona = PropiedadPersona.objects.get(persona=request.user, estado='activo')
        has_active_contract = True
    except PropiedadPersona.DoesNotExist:
        return redirect('dashboard')

    if request.method == 'POST':
        form = ResidentePreAutorizacionForm(request.POST)
        if form.is_valid():
            autorizacion = form.save(commit=False)
            autorizacion.residente = request.user
            autorizacion.propiedad = propiedad_persona.propiedad
            autorizacion.estado = 'pendiente'
            autorizacion.save()
            return redirect('mis_preautorizaciones')
    else:
        form = ResidentePreAutorizacionForm()

    context = {
        'has_active_contract': has_active_contract,
        'form': form
    }
    return render(request, 'complejos/form_preautorizacion.html', context)

@login_required
@user_passes_test(es_residente)
def editar_preautorizacion_view(request, pa_id):
    if not PropiedadPersona.objects.filter(persona=request.user, estado='activo').exists():
        return redirect('dashboard')

    autorizacion = get_object_or_404(PreAutorizacion, id=pa_id, residente=request.user)
    

    if autorizacion.estado != 'pendiente':
        return redirect('mis_preautorizaciones')

    if request.method == 'POST':
        form = ResidentePreAutorizacionForm(request.POST, instance=autorizacion)
        if form.is_valid():
            form.save()
            return redirect('mis_preautorizaciones')
    else:
        form = ResidentePreAutorizacionForm(instance=autorizacion)

    context = {
        'has_active_contract': True,
        'form': form,
        'autorizacion': autorizacion
    }
    return render(request, 'complejos/form_preautorizacion.html', context)

@login_required
@user_passes_test(es_residente)
def cancelar_preautorizacion_view(request, pa_id):
    if not PropiedadPersona.objects.filter(persona=request.user, estado='activo').exists():
        return redirect('dashboard')

    autorizacion = get_object_or_404(PreAutorizacion, id=pa_id, residente=request.user)

    if request.method == 'POST':
        if autorizacion.estado == 'pendiente':
            autorizacion.estado = 'cancelado'
            autorizacion.save()
        return redirect('mis_preautorizaciones')

    context = {
        'has_active_contract': True,
        'autorizacion': autorizacion
    }
    return render(request, 'complejos/cancelar_preautorizacion.html', context)

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
