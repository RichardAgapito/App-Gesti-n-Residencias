from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.contrib import messages
from .models import Aviso
from .forms import AvisoForm

class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user is an admin (staff).
    """
    def test_func(self):
        return self.request.user.is_staff

class ListaAvisos(LoginRequiredMixin, ListView):
    """
    Muestra la lista de avisos para el complejo del usuario.
    """
    model = Aviso
    template_name = 'avisos/lista_avisos.html'
    context_object_name = 'avisos'

    def get_queryset(self):
        user = self.request.user

        # Admin Logic (Staff)
        if user.is_staff and user.rol != 'GERENTE':
            return Aviso.objects.filter(autor=user).order_by('-fecha_creacion')
        
        # Manager Logic
        if user.rol == 'GERENTE':
            if hasattr(user, 'complejo_asignado') and user.complejo_asignado:
                # Manager sees all notices for their complex (or just theirs? User said "should be the same")
                # But creating restricted to complex. 
                # Let's show all notices for the complex so they can manage them.
                return Aviso.objects.filter(complejo=user.complejo_asignado).order_by('-fecha_creacion')
            else:
                return Aviso.objects.none()

        # Resident Logic
        propiedad_activa = user.propiedades_asociadas.filter(estado='activo').first()
        if propiedad_activa:
            complejo_residente = propiedad_activa.propiedad.complejo
            return Aviso.objects.filter(complejo=complejo_residente).order_by('-fecha_creacion')
        
        return Aviso.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        queryset = self.get_queryset()
        
        # Residents (not staff/manager) care about unread count
        if not user.is_staff and user.rol != 'GERENTE':
             context['avisos_no_leidos'] = queryset.exclude(leido_por=user).count()
        
        return context

class DetalleAviso(LoginRequiredMixin, DetailView):
    """
    Muestra el detalle de un aviso y lo marca como leído.
    """
    model = Aviso
    template_name = 'avisos/detalle_aviso.html'
    context_object_name = 'aviso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aviso = self.get_object()

        aviso.leido_por.add(self.request.user)
        return context

class AdminOrManagerRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user is an admin or manager.
    """
    def test_func(self):
        user = self.request.user
        return user.is_staff or user.rol == 'GERENTE'

class CrearAviso(LoginRequiredMixin, AdminOrManagerRequiredMixin, CreateView):
    """
    Permite a los administradores y gerentes crear un nuevo aviso.
    """
    model = Aviso
    form_class = AvisoForm
    template_name = 'avisos/crear_aviso.html'
    success_url = reverse_lazy('avisos:lista_avisos')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        
        # If user is a Manager, restrict the 'complejo' field
        if user.rol == 'GERENTE' and hasattr(user, 'complejo_asignado') and user.complejo_asignado:
            from complejos.models import Complejo
            # Set the queryset to only include their assigned complex
            form.fields['complejo'].queryset = Complejo.objects.filter(pk=user.complejo_asignado.pk)
            # Set initial value and empty label
            form.fields['complejo'].initial = user.complejo_asignado
            form.fields['complejo'].empty_label = None
            
        return form

    def form_valid(self, form):
        form.instance.autor = self.request.user
        messages.success(self.request, 'Aviso creado y enviado con éxito.')
        return super().form_valid(form)
