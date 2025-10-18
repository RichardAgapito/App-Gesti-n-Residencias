from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import CustomUserCreationForm # <-- Importamos nuestro nuevo formulario
from .models import Profile 

@login_required
def dashboard(request):
    return render(request, 'users/dashboard.html')



def es_admin(user):
    return user.is_authenticated and user.profile.role == 'ADMIN'

@user_passes_test(es_admin, login_url='/') 
def crear_usuario_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            
            Profile.objects.create(
                user=new_user,
                role=form.cleaned_data.get('role')
            )
            return redirect('/') 
    else:
        form = CustomUserCreationForm()
        
    return render(request, 'users/crear_usuario.html', {'form': form})