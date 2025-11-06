from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse
from .models import Complejo, Propiedad, PropiedadPersona
from .forms import ComplejoForm, PropiedadForm, CrearPropiedadesMultiplesForm, EditarPropiedadForm, PropiedadPersonaForm
from users.views import es_admin
from django.contrib.auth import get_user_model


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
    context = {
        'propiedad': propiedad,
    }
    return render(request, 'complejos/detalle_propiedad.html', context)


@user_passes_test(es_admin, login_url='/')
def asignar_contrato(request, propiedad_id):
    propiedad = get_object_or_404(Propiedad, id=propiedad_id)
    if request.method == 'POST':
        form = PropiedadPersonaForm(request.POST, propiedad=propiedad)
        if form.is_valid():
            print(f"Persona 2: {form.cleaned_data['persona2']}")
            tipo_relacion = form.cleaned_data['tipo_relacion']
            propiedad_persona = PropiedadPersona(
                propiedad=propiedad,
                persona=form.cleaned_data['persona'],
                tipo_relacion=tipo_relacion,
                porcentaje_propiedad=form.cleaned_data['porcentaje_propiedad'],
                fecha_inicio=form.cleaned_data['fecha_inicio'],
                fecha_fin=form.cleaned_data['fecha_fin'],
                es_principal=True,
                estado=form.cleaned_data['estado']
            )
            propiedad_persona.save()

            if tipo_relacion in ['co-propietario', 'co-inquilino']:
                # Create second person
                asignacion2 = PropiedadPersona(
                    propiedad=propiedad,
                    persona=form.cleaned_data['persona2'],
                    tipo_relacion=tipo_relacion,
                    porcentaje_propiedad=form.cleaned_data['porcentaje_propiedad'],
                    fecha_inicio=form.cleaned_data['fecha_inicio'],
                    fecha_fin=form.cleaned_data['fecha_fin'],
                    es_principal=False,  # The second person cannot be principal
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
            form.save()
            return redirect('detalle_propiedad', propiedad_id=propiedad.id)
    else:
        form = EditarPropiedadForm(instance=propiedad)
    return render(request, 'complejos/editar_propiedad.html', {'form': form, 'propiedad': propiedad})

def get_residentes_json(request):
    residentes = get_user_model().objects.filter(rol='RESIDENTE').values('id', 'persona__nombres', 'persona__apellidos')
    return JsonResponse(list(residentes), safe=False)
