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
        # Los administradores pueden ver los avisos que han enviado
        if user.is_staff:
            return Aviso.objects.filter(autor=user).order_by('-fecha_creacion')
        
        # Lógica corregida para residentes: Obtener complejo a través de la propiedad
        propiedad_activa = user.propiedades_asociadas.filter(estado='activo').first()
        if propiedad_activa:
            complejo_residente = propiedad_activa.propiedad.complejo
            return Aviso.objects.filter(complejo=complejo_residente).order_by('-fecha_creacion')
        
        return Aviso.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        queryset = self.get_queryset()
        
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
        # Marcar como leído al verlo
        aviso.leido_por.add(self.request.user)
        return context

class CrearAviso(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """
    Permite a los administradores crear un nuevo aviso.
    """
    model = Aviso
    form_class = AvisoForm
    template_name = 'avisos/crear_aviso.html'
    success_url = reverse_lazy('avisos:lista_avisos')

    def form_valid(self, form):
        form.instance.autor = self.request.user
        messages.success(self.request, 'Aviso creado y enviado con éxito.')
        return super().form_valid(form)