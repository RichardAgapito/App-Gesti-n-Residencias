# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CustomUserCreationForm # <-- Importamos nuestro nuevo formulario
from .models import Profile # <-- Importamos el modelo Profile

# --- La vista del Dashboard (ya la tienes) ---
@login_required
def dashboard(request):
    return render(request, 'users/dashboard.html')


# --- AÑADE ESTA NUEVA VISTA COMPLETA ---

# Esta función verifica si el usuario tiene el rol de ADMIN
def es_admin(user):
    return user.is_authenticated and user.profile.role == 'ADMIN'

@user_passes_test(es_admin, login_url='/') # Protegemos la vista
def crear_usuario_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            # 1. Guarda el nuevo usuario
            new_user = form.save()
            
            # 2. Crea el perfil asociado a ese usuario
            Profile.objects.create(
                user=new_user,
                role=form.cleaned_data.get('role')
            )
            return redirect('/') # Redirige al dashboard principal después de crear
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'users/crear_usuario.html', {'form': form})