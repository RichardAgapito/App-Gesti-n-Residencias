from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.contrib import messages
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .forms import CustomUserCreationForm, EditarUsuarioForm
from .models import CustomUser
from avisos.models import Aviso
from complejos.models import Complejo
from complejos.models import PropiedadPersona
from django.http import JsonResponse
from django.template.loader import render_to_string
from finanzas.models import Factura

@login_required
def dashboard(request):
    if request.user.rol == 'ADMIN':
        from django.db.models import Count, Q
        from datetime import timedelta
        from django.utils import timezone
        
        # Estadísticas básicas
        total_usuarios = CustomUser.objects.count()
        total_complejos = Complejo.objects.count()
        visitas_hoy = 0

        # Calcular ocupación por complejo
        complejos_data = []
        complejos = Complejo.objects.all()
        for complejo in complejos:
            total_propiedades = complejo.propiedades.count()
            if total_propiedades > 0:
                propiedades_ocupadas = complejo.propiedades.filter(estado_ocupacion='ocupado').count()
                porcentaje_ocupacion = int((propiedades_ocupadas / total_propiedades) * 100)
                complejos_data.append({
                    'nombre': complejo.nombre,
                    'ocupacion': porcentaje_ocupacion,
                    'unidades': total_propiedades
                })

        # Actividad reciente (últimos 7 días)
        hace_7_dias = timezone.now() - timedelta(days=7)
        actividad_reciente = []

        # Usuarios recientes
        usuarios_recientes = CustomUser.objects.filter(date_joined__gte=hace_7_dias).order_by('-date_joined')[:3]
        for usuario in usuarios_recientes:
            actividad_reciente.append({
                'tipo': 'usuario',
                'descripcion': f'Nuevo usuario registrado: {usuario.persona.nombres if usuario.persona else usuario.email}',
                'tiempo': usuario.date_joined
            })

        # Avisos recientes
        avisos_recientes = Aviso.objects.filter(fecha_creacion__gte=hace_7_dias).order_by('-fecha_creacion')[:2]
        for aviso in avisos_recientes:
            actividad_reciente.append({
                'tipo': 'aviso',
                'descripcion': f'Nuevo aviso publicado: {aviso.titulo}',
                'tiempo': aviso.fecha_creacion
            })

        # Ordenar por tiempo (más reciente primero)
        actividad_reciente.sort(key=lambda x: x['tiempo'], reverse=True)
        actividad_reciente = actividad_reciente[:5]  # Limitar a 5 items

        context = {
            'total_usuarios': total_usuarios,
            'total_complejos': total_complejos,
            'visitas_hoy': visitas_hoy,
            'complejos_data': complejos_data,
            'actividad_reciente': actividad_reciente,
        }
        return render(request, 'users/dashboard.html', context)
    
    elif request.user.rol == 'GERENTE':
        context = {
            'complejo': request.user.complejo_asignado,
        }
        return render(request, 'users/dashboard.html', context)
    
    elif request.user.rol == 'GUARDIA':
        return redirect('dashboard_visitas')
    
    else:

        user = request.user
        avisos_recientes = Aviso.objects.none()
        

        propiedad_activa = user.propiedades_asociadas.filter(estado='activo').first()
        if propiedad_activa:
            complejo_residente = propiedad_activa.propiedad.complejo
            avisos_recientes = Aviso.objects.filter(
                complejo=complejo_residente
            ).exclude(leido_por=user).order_by('-fecha_creacion')[:5]

        context = {
            'avisos_recientes': avisos_recientes,
        }
        return render(request, 'users/dashboard.html', context)


def es_admin(user):
    return user.is_authenticated and user.rol == CustomUser.Rol.ADMIN

def es_residente(user):
    return user.is_authenticated and user.rol == CustomUser.Rol.RESIDENTE

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
