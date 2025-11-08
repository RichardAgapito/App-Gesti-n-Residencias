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
        return Aviso.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Obtener el tipo de vista (recibidos/enviados)
        vista = self.request.GET.get('vista', 'recibidos')
        context['vista_actual'] = vista
        
        if vista == 'enviados':
            # Vista de enviados - mostrar los avisos creados por el usuario
            avisos_query = Aviso.objects.filter(autor=user)
            context['avisos'] = avisos_query.order_by('-fecha_creacion')
            context['avisos_no_leidos'] = 0  # Los enviados no tienen contador de no leídos
        else:
            # Vista de recibidos - filtrar según el rol del usuario
            if user.is_superuser:
                # Superusuario ve todos los avisos excepto los propios
                avisos_query = Aviso.objects.exclude(autor=user)
            elif user.is_staff and user.complejo_asignado:
                # Staff ve avisos de su complejo excepto los propios
                avisos_query = Aviso.objects.filter(
                    complejo=user.complejo_asignado
                ).exclude(autor=user)
            elif user.complejo_asignado:
                # Residentes ven avisos dirigidos a ellos en su complejo
                avisos_query = Aviso.objects.filter(
                    Q(complejo=user.complejo_asignado) &
                    Q(dirigido_a__in=[Aviso.DirigidoA.TODOS, Aviso.DirigidoA.RESIDENTES])
                ).exclude(autor=user)
            else:
                avisos_query = Aviso.objects.none()
            
            # Ordenar por fecha y contar no leídos
            context['avisos'] = avisos_query.order_by('-fecha_creacion')
            context['avisos_no_leidos'] = avisos_query.exclude(leido_por=user).count()
        
        return context

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
        if not self.request.user.is_staff:
            form.instance.complejo = self.request.user.complejo_asignado
        return super().form_valid(form)

@login_required
def marcar_como_leido(request, pk):
    aviso = get_object_or_404(Aviso, pk=pk)
    aviso.leido_por.add(request.user)
    return redirect('avisos:detalle_aviso', pk=pk)