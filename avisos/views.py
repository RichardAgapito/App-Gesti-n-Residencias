from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Aviso
from .forms import AvisoForm
from users.models import CustomUser

class ListaAvisos(LoginRequiredMixin, ListView):
    model = Aviso
    template_name = 'avisos/lista_avisos.html'
    context_object_name = 'avisos'

    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser:
            # Superusuario ve todos los avisos
            return Aviso.objects.all()
        
        if user.is_staff:
            # Personal de staff ve todos los avisos de su complejo
            if user.complejo_asignado:
                return Aviso.objects.filter(complejo=user.complejo_asignado)
            else:
                # Si el staff no tiene complejo, no ve ninguno (o todos, según se decida)
                return Aviso.objects.none() 
        else:
            # Residente ve avisos públicos de su complejo y los que él mismo ha creado
            complejo_residente = user.complejo_asignado
            if not complejo_residente:
                return Aviso.objects.none()

            return Aviso.objects.filter(
                Q(complejo=complejo_residente) & 
                (
                    Q(dirigido_a__in=[Aviso.DirigidoA.TODOS, Aviso.DirigidoA.RESIDENTES]) |
                    Q(autor=user)
                )
            )

class DetalleAviso(LoginRequiredMixin, DetailView):
    model = Aviso
    template_name = 'avisos/detalle_aviso.html'
    context_object_name = 'aviso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        aviso = self.get_object()
        aviso.leido_por.add(self.request.user)
        return context

class CrearAviso(LoginRequiredMixin, CreateView):
    model = Aviso
    form_class = AvisoForm
    template_name = 'avisos/crear_aviso.html'
    success_url = reverse_lazy('avisos:lista_avisos')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.autor = self.request.user
        # Si el usuario no es staff, el complejo se asigna automáticamente.
        # Si es staff, el complejo viene del formulario.
        if not self.request.user.is_staff:
            form.instance.complejo = self.request.user.complejo_asignado
        return super().form_valid(form)

@login_required
def marcar_como_leido(request, pk):
    aviso = get_object_or_404(Aviso, pk=pk)
    aviso.leido_por.add(request.user)
    return redirect('avisos:detalle_aviso', pk=pk)