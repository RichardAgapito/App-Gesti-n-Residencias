from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from .models import Aviso
from .forms import AvisoForm
from users.models import CustomUser


class ListaAvisos(LoginRequiredMixin, ListView):
    model = Aviso
    template_name = 'avisos/lista_avisos.html'
    context_object_name = 'avisos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Obtener el tipo de vista (recibidos/enviados)
        vista = self.request.GET.get('vista', 'recibidos')
        context['vista_actual'] = vista

        # Siempre inicializar la variable avisos
        avisos = Aviso.objects.none()

        # Filtrar avisos según la vista seleccionada
        if vista == 'enviados':
            # Avisos que YO envié
            avisos = Aviso.objects.filter(autor=user)
            
        else:  # recibidos
            if user.is_superuser:
                # Superusuario ve todos los avisos excepto los que él creó
                avisos = Aviso.objects.exclude(autor=user)
                
            elif user.is_staff and user.complejo_asignado:
                # ADMINISTRADORES ven:
                # 1. Avisos dirigidos a TODOS o ADMINISTRADORES
                # 2. Avisos de RESIDENTES (para que vean lo que envían los residentes)
                avisos = Aviso.objects.filter(
                    complejo=user.complejo_asignado
                ).filter(
                    Q(dirigido_a__in=[Aviso.DirigidoA.TODOS, Aviso.DirigidoA.ADMINISTRADORES]) |
                    Q(autor__is_staff=False)  # Avisos enviados por residentes
                ).exclude(autor=user)
                
            elif user.complejo_asignado:
                # RESIDENTES ven:
                # 1. Avisos dirigidos a TODOS o RESIDENTES
                # 2. Avisos de ADMINISTRADORES (para que vean lo que envían los admins)
                avisos = Aviso.objects.filter(
                    complejo=user.complejo_asignado
                ).filter(
                    Q(dirigido_a__in=[Aviso.DirigidoA.TODOS, Aviso.DirigidoA.RESIDENTES]) |
                    Q(autor__is_staff=True)  # Avisos enviados por administradores
                ).exclude(autor=user)
                
            else:
                avisos = Aviso.objects.none()

        # Ordenar por fecha de creación
        avisos = avisos.order_by('-fecha_creacion')

        # Contar avisos no leídos (solo para la vista de recibidos)
        if vista == 'recibidos':
            context['avisos_no_leidos'] = avisos.exclude(leido_por=user).count()
        else:
            context['avisos_no_leidos'] = 0

        context['avisos'] = avisos
        return context

    def get_queryset(self):
        return Aviso.objects.none()


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

    def get(self, request, *args, **kwargs):
        # Para residentes, verificar que tengan un complejo asignado.
        if not request.user.is_staff and not request.user.complejo_asignado:
            messages.error(request, 'No tienes un complejo asignado. Contacta al administrador para que te asigne uno.')
            return redirect('avisos:lista_avisos')
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.autor = self.request.user
        # Si el usuario no es staff, el complejo se asigna automáticamente.
        if not self.request.user.is_staff:
            form.instance.complejo = self.request.user.complejo_asignado
        
        messages.success(self.request, 'Aviso creado con éxito.')
        return super().form_valid(form)


@login_required
def marcar_como_leido(request, pk):
    """
    Vista para marcar un aviso como leído manualmente
    """
    aviso = get_object_or_404(Aviso, pk=pk)
    aviso.leido_por.add(request.user)
    return redirect('avisos:detalle_aviso', pk=pk)
