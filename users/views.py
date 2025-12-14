from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .forms import CustomUserCreationForm, EditarUsuarioForm
from .models import CustomUser
from avisos.models import Aviso
from complejos.models import Complejo
from complejos.models import Complejo, PropiedadPersona, Reserva
from django.http import JsonResponse
from django.template.loader import render_to_string
from finanzas.models import Factura, ContratoFinanciero, Recaudo

from django.db.models import Count, Sum
from visitas.models import Visita

@login_required
def dashboard(request):
    if request.user.rol == 'ADMIN':
        
        # Estadísticas básicas
        total_usuarios = CustomUser.objects.count()
        total_complejos = Complejo.objects.count()
        visitas_hoy = Visita.objects.filter(fecha_hora_ingreso__date=timezone.now().date()).count()
        
        # Ingresos del mes
        ingresos_mes = Recaudo.objects.filter(
            fecha_pago__month=timezone.now().month,
            fecha_pago__year=timezone.now().year
        ).aggregate(Sum('monto_pagado'))['monto_pagado__sum'] or 0

        # Calcular ocupación por complejo
        complejos_data = []
        # Usar prefetch para optimizar
        complejos = Complejo.objects.prefetch_related('propiedades', 'propiedades__personas_asociadas').all()
        
        for complejo in complejos:
            total_propiedades = complejo.propiedades.count()
            occupied_count = 0
            
            # Calcular ocupación real
            for p in complejo.propiedades.all():
                is_occupied_manual = (p.estado_ocupacion == 'ocupado')
                has_active_relation = False
                for relation in p.personas_asociadas.all():
                    if relation.estado == 'activo' and relation.tipo_relacion in ['inquilino', 'propietario']:
                        has_active_relation = True
                        break
                
                if is_occupied_manual or has_active_relation:
                    occupied_count += 1

            # Usar la cantidad de propiedades creadas (no la planificada)
            denominator = total_propiedades
            
            porcentaje_ocupacion = int((occupied_count / denominator) * 100) if denominator > 0 else 0
            
            complejos_data.append({
                'nombre': complejo.nombre,
                'ocupacion': porcentaje_ocupacion,
                'unidades': denominator
            })

        # Actividad reciente (últimos 30 días o sin límite para dev)
        # hace_7_dias = timezone.now() - timedelta(days=7) # Comentado para mostrar más actividad
        actividad_reciente = []

        # Usuarios recientes (últimos 10 registrados)
        usuarios_recientes = CustomUser.objects.all().order_by('-date_joined')[:5]
        for usuario in usuarios_recientes:
            actividad_reciente.append({
                'tipo': 'usuario',
                'descripcion': f'Nuevo usuario registrado: {usuario.persona.nombres if usuario.persona else usuario.email}',
                'tiempo': usuario.date_joined
            })

        # Avisos recientes (últimos 5)
        avisos_recientes = Aviso.objects.all().order_by('-fecha_creacion')[:5]
        for aviso in avisos_recientes:
            actividad_reciente.append({
                'tipo': 'aviso',
                'descripcion': f'Nuevo aviso publicado: {aviso.titulo}',
                'tiempo': aviso.fecha_creacion
            })

        # Ordenar por tiempo (más reciente primero)
        actividad_reciente.sort(key=lambda x: x['tiempo'], reverse=True)
        actividad_reciente = actividad_reciente[:10]  # Limitar a 10 items

        context = {
            'total_usuarios': total_usuarios,
            'total_complejos': total_complejos,
            'visitas_hoy': visitas_hoy,
            'ingresos_mes': ingresos_mes,
            'complejos_data': complejos_data,
            'actividad_reciente': actividad_reciente,
        }
        return render(request, 'users/dashboard.html', context)
    
    elif request.user.rol == 'GERENTE':
        complejo = request.user.complejo_asignado
        context = {}
        
        if complejo:
            # 1. Stats Básicos
            total_propiedades = complejo.propiedades.count()
            total_amenidades = complejo.amenidades.count()
            
            # 2. Reservas Pendientes
            # Support both direct FK and legacy relation for robustness
            reservas_pendientes = Reserva.objects.filter(
                Q(complejo=complejo) | Q(amenidad__complejo=complejo),
                estado='pendiente'
            ).distinct().count()

            # 3. Ocupación
            occupied_count = 0
            propiedades = complejo.propiedades.prefetch_related('personas_asociadas').all()
            for p in propiedades:
                is_occupied_manual = (p.estado_ocupacion == 'ocupado')
                has_active_relation = False
                for relation in p.personas_asociadas.all():
                    if relation.estado == 'activo' and relation.tipo_relacion in ['inquilino', 'propietario']:
                        has_active_relation = True
                        break
                if is_occupied_manual or has_active_relation:
                    occupied_count += 1
            
            denominator = total_propiedades
            porcentaje_ocupacion = int((occupied_count / denominator) * 100) if denominator > 0 else 0

            # 4. Actividad Reciente (Reservas recientes en el complejo)
            actividad_reciente = []
            reservas_recientes = Reserva.objects.filter(
                Q(complejo=complejo) | Q(amenidad__complejo=complejo)
            ).order_by('-fecha_creacion')[:5]

            for reserva in reservas_recientes:
                actividad_reciente.append({
                    'tipo': 'reserva',
                    'descripcion': f'Nueva reserva: {reserva.amenidad.nombre} - {reserva.residente.persona.nombres}',
                    'tiempo': reserva.fecha_creacion, # Assuming created_at exists, if not use an available date field
                    'estado': reserva.estado
                })
            
            # Also check for new contracts
            nuevos_contratos = PropiedadPersona.objects.filter(
                propiedad__complejo=complejo,
                fecha_inicio__gte=timezone.now() - timedelta(days=30)
            ).order_by('-fecha_inicio')[:5]

            for contrato in nuevos_contratos:
                actividad_reciente.append({
                    'tipo': 'contrato',
                    'descripcion': f'Nuevo contrato: {contrato.propiedad.numero_identificador} - {contrato.tipo_relacion}',
                    'tiempo': contrato.fecha_inicio,
                    'estado': contrato.estado
                })
            
            # Sort combined activity
            # Note: mixed types (datetime vs date) might cause sort issues if not handled carefully. 
            # safe sort key:
            def get_time(item):
                t = item['tiempo']
                # Convert date to datetime if needed
                if not hasattr(t, 'hour'):
                    return timezone.make_aware(timezone.datetime.combine(t, timezone.datetime.min.time()))
                return t
            
            actividad_reciente.sort(key=get_time, reverse=True)
            actividad_reciente = actividad_reciente[:10]

            # 5. Operational Metrics - Option E (Only Daily Aggenda)
            # Reservas confirmadas para HOY (Agenda del día)
            reservas_hoy_count = Reserva.objects.filter(
                Q(complejo=complejo) | Q(amenidad__complejo=complejo),
                estado='confirmada',
                fecha_inicio__date=timezone.now().date()
            ).count()

            context = {
                'complejo': complejo,
                'total_propiedades': total_propiedades,
                'total_amenidades': total_amenidades,
                'reservas_pendientes': reservas_pendientes,
                'porcentaje_ocupacion': porcentaje_ocupacion,
                'actividad_reciente': actividad_reciente,
                'reservas_hoy_count': reservas_hoy_count,
            }
        else:
             context = {
                'error_mensaje': "No tienes un complejo asignado. Contacta al administrador."
            }
        
        return render(request, 'users/dashboard.html', context)
    
    elif request.user.rol == 'GUARDIA':
        return redirect('dashboard_visitas')
    
    else:
        user = request.user
        avisos_recientes = Aviso.objects.none()
        
        # Obtener contrato de propiedad activo
        propiedad_contrato = user.propiedades_asociadas.filter(estado='activo').first()
        
        # Variables por defecto
        deuda_total = 0
        facturas_vencidas_count = 0
        timeline_facturas = []
        contrato_financiero = None
        reservas_activas_count = 0
        reservas_proximas = []
        proximo_pago = None
        
        if propiedad_contrato:
            complejo_residente = propiedad_contrato.propiedad.complejo
            
            # Avisos
            avisos_recientes = Aviso.objects.filter(
                complejo=complejo_residente
            ).exclude(leido_por=user).order_by('-fecha_creacion')[:5]

            # --- LÓGICA FINANCIERA ---
            
            # 1. Totales de Deuda
            facturas_pendientes = Factura.objects.filter(
                propiedad=propiedad_contrato.propiedad,
                estado__in=['PENDIENTE', 'VENCIDA']
            )
            for factura in facturas_pendientes:
                deuda_total += factura.total_calculado
                if factura.estado == 'VENCIDA':
                    facturas_vencidas_count += 1
            
            # 2. Datos para la Línea de Tiempo (Últimas 6 + Próximas)
            # Traemos todas para que el template las pinte en orden
            timeline_facturas = Factura.objects.filter(
                propiedad=propiedad_contrato.propiedad
            ).order_by('fecha_vencimiento') # Orden cronológico (antiguas -> nuevas)

            # 3. Datos del Contrato Financiero (Progreso de Cuotas)
            contrato_financiero = ContratoFinanciero.objects.filter(
                propiedad_persona=propiedad_contrato,
                estado='ACTIVO'
            ).first()

            # 4. Datos de Reservas
            now = timezone.now()
            reservas_activas_count = Reserva.objects.filter(
                residente=user, 
                estado__in=['pendiente', 'confirmada'],
                fecha_inicio__month=now.month,
                fecha_inicio__year=now.year
            ).count()

            reservas_proximas = Reserva.objects.filter(
                residente=user,
                fecha_inicio__gte=now
            ).order_by('fecha_inicio')[:5]
            
            # 5. Próximo Pago (Primera factura pendiente)
            proximo_pago = Factura.objects.filter(
                propiedad=propiedad_contrato.propiedad,
                estado__in=['PENDIENTE', 'VENCIDA']
            ).order_by('fecha_vencimiento').first()

        context = {
            'avisos_recientes': avisos_recientes,
            'deuda_total': deuda_total,
            'facturas_vencidas_count': facturas_vencidas_count,
            'tiene_propiedad': propiedad_contrato is not None,
            # Nuevos datos al contexto:
            'timeline_facturas': timeline_facturas,
            'contrato_financiero': contrato_financiero,
            'reservas_activas_count': reservas_activas_count,
            'reservas_proximas': reservas_proximas,
            'proximo_pago': proximo_pago,
            'complejo_nombre': complejo_residente.nombre if propiedad_contrato else None,
        }
        return render(request, 'users/dashboard.html', context)

        context = {
            'avisos_recientes': avisos_recientes,
            'deuda_total': deuda_total,
            'facturas_vencidas_count': facturas_vencidas_count,
            'tiene_propiedad': propiedad_contrato is not None
        }
        return render(request, 'users/dashboard.html', context)


def es_admin(user):
    return user.is_authenticated and user.rol == CustomUser.Rol.ADMIN

def es_residente(user):
    return user.is_authenticated and user.rol == CustomUser.Rol.RESIDENTE

def es_admin_o_gerente(user):
    return user.is_authenticated and (user.rol == CustomUser.Rol.ADMIN or user.rol == CustomUser.Rol.GERENTE)

@user_passes_test(es_admin, login_url='/')
def crear_usuario_view(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse({'success': True})
            return redirect('lista_usuarios')
        elif is_ajax:
            html = render_to_string('users/partials/crear_usuario_partial.html', {'form': form}, request=request)
            return JsonResponse({'success': False, 'html': html})
    else:
        form = CustomUserCreationForm()

    template = 'users/partials/crear_usuario_partial.html' if is_ajax else 'users/crear_usuario.html'
    return render(request, template, {'form': form})

@user_passes_test(es_admin, login_url='/')
def lista_usuarios_view(request):
    users = CustomUser.objects.all().select_related('persona')

    query = request.GET.get('q')
    if query:
        users = users.filter(
            Q(email__icontains=query) |
            Q(persona__nombres__icontains=query) |
            Q(persona__apellidos__icontains=query)
        )

    rol_filter = request.GET.get('rol')
    if rol_filter:
        users = users.filter(rol=rol_filter)

    estado_filter = request.GET.get('estado')
    if estado_filter is not None and estado_filter != '':
        users = users.filter(is_active=(estado_filter == 'True'))

    context = {
        'users': users,
        'rol_choices': CustomUser.Rol.choices,
        'current_rol': rol_filter,
        'current_estado': estado_filter,
    }
    return render(request, 'users/lista_usuarios.html', context)

@user_passes_test(es_admin, login_url='/')
def detalle_usuario_view(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    context = {'user': user}
    template = 'users/partials/detalle_usuario_partial.html' if is_ajax else 'users/detalle_usuario.html'
    return render(request, template, context)

@user_passes_test(es_admin, login_url='/')
def editar_usuario_view(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    persona = user.persona
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=persona, user=user)
        if form.is_valid():
            persona = form.save(commit=False)
            user.is_active = form.cleaned_data['is_active']
            persona.save()
            user.save()
            if is_ajax:
                return JsonResponse({'success': True})
            return redirect('detalle_usuario', user_id=user.id)
        elif is_ajax:
            html = render_to_string('users/partials/editar_usuario_partial.html', {'form': form, 'user': user}, request=request)
            return JsonResponse({'success': False, 'html': html})
    else:
        form = EditarUsuarioForm(instance=persona, user=user)

    context = {'form': form, 'user': user}
    template = 'users/partials/editar_usuario_partial.html' if is_ajax else 'users/editar_usuario.html'
    return render(request, template, context)

@user_passes_test(es_admin, login_url='/')
@require_POST
def toggle_user_active(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if not user.is_superuser:
        user.is_active = not user.is_active
        user.save()
    return redirect('lista_usuarios')

class ContratoResidenteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'users/ver_contrato_residente.html'

    def test_func(self):
        return es_residente(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Get the active contract for the logged-in resident
        contrato_activo = PropiedadPersona.objects.filter(persona=user, estado='activo').first()
        
        context['contrato_activo'] = contrato_activo
        return context
