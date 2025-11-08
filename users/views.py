from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.db.models import Q
from .forms import CustomUserCreationForm, EditarUsuarioForm
from .models import CustomUser
from complejos.models import Complejo
from complejos.models import PropiedadPersona

@login_required
def dashboard(request):
    if request.user.rol == 'ADMIN':
        
        # --- ESTAS LÍNEAS FALTABAN ---
        total_usuarios = CustomUser.objects.count()
        total_complejos = Complejo.objects.count()
        visitas_hoy = 0  # Placeholder
        # -----------------------------

        context = {
            'total_usuarios': total_usuarios,
            'total_complejos': total_complejos,
            'visitas_hoy': visitas_hoy,
        }
        return render(request, 'users/dashboard.html', context)
    
    elif request.user.rol == 'GUARDIA':
        return redirect('dashboard_visitas')
    
    else:
        # Esta parte ya estaba correcta
        has_active_contract = PropiedadPersona.objects.filter(persona=request.user, estado='activo').exists()
        
        context = {
            'has_active_contract': has_active_contract
        }
        return render(request, 'users/dashboard.html', context)

def es_admin(user):
    return user.is_authenticated and user.rol == CustomUser.Rol.ADMIN

@user_passes_test(es_admin, login_url='/')
def crear_usuario_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('/')
    else:
        form = CustomUserCreationForm()

    return render(request, 'users/crear_usuario.html', {'form': form})

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
    context = {
        'user': user
    }
    return render(request, 'users/detalle_usuario.html', context)

@user_passes_test(es_admin, login_url='/')
def editar_usuario_view(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    persona = user.persona

    if request.method == 'POST':
        form = EditarUsuarioForm(request.POST, instance=persona, user=user)
        if form.is_valid():
            persona = form.save(commit=False)
            user.is_active = form.cleaned_data['is_active']
            persona.save()
            user.save()
            return redirect('detalle_usuario', user_id=user.id)
    else:
        form = EditarUsuarioForm(instance=persona, user=user)

    context = {
        'form': form,
        'user': user
    }
    return render(request, 'users/editar_usuario.html', context)

@user_passes_test(es_admin, login_url='/')
@require_POST
def toggle_user_active(request, user_id):
    user = get_object_or_404(CustomUser, id=user_id)
    if not user.is_superuser:
        user.is_active = not user.is_active
        user.save()
    return redirect('lista_usuarios')