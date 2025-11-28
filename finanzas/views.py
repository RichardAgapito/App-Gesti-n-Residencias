from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from .models import PlanCuota, ConceptoCobro, MetodoPago, Factura, Recaudo
from .forms import PlanCuotaForm, ConceptoCobroForm, MetodoPagoForm, FacturaForm, DetalleFacturaFormSet, RecaudoForm
from django.db import transaction, models
from django.shortcuts import get_object_or_404, redirect, reverse
from django.contrib import messages
from django.core.management import call_command
from io import StringIO

class AdminRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user has the ADMIN role.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.rol == 'ADMIN'

class GerenteRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user has the GERENTE role.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.rol == 'GERENTE'

class ResidenteRequiredMixin(UserPassesTestMixin):
    """
    Mixin to ensure the user has the RESIDENTE role.
    """
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.rol == 'RESIDENTE'

# Vistas para PlanCuota
class PlanCuotaListView(LoginRequiredMixin, ListView):
    model = PlanCuota
    template_name = 'finanzas/lista_planes_cuota.html'
    context_object_name = 'planes'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.rol == 'ADMIN' or request.user.rol == 'GERENTE'):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'ADMIN':
            return PlanCuota.objects.all()
        elif user.rol == 'GERENTE' and user.complejo_asignado:
            return PlanCuota.objects.filter(complejo=user.complejo_asignado)
        return PlanCuota.objects.none()

class PlanCuotaCreateView(LoginRequiredMixin, CreateView):
    model = PlanCuota
    form_class = PlanCuotaForm
    template_name = 'finanzas/crear_plan_cuota.html'
    success_url = reverse_lazy('lista_planes_cuota')

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.rol == 'ADMIN' or request.user.rol == 'GERENTE'):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['conceptos_formset'] = PlanConceptoCobroFormSet(self.request.POST, form_kwargs={'complejo': self._get_complejo()})
        else:
            data['conceptos_formset'] = PlanConceptoCobroFormSet(form_kwargs={'complejo': self._get_complejo()})
        return data

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        conceptos_formset = PlanConceptoCobroFormSet(request.POST, form_kwargs={'complejo': self._get_complejo()})

        if form.is_valid() and conceptos_formset.is_valid():
            return self.form_valid(form, conceptos_formset)
        else:
            return self.form_invalid(form, conceptos_formset)

    def form_valid(self, form, conceptos_formset):
        with transaction.atomic():
            if self.request.user.rol == 'GERENTE' and self.request.user.complejo_asignado:
                form.instance.complejo = self.request.user.complejo_asignado
            
            self.object = form.save()
            conceptos_formset.instance = self.object
            conceptos_formset.save()

        messages.success(self.request, "Plan de cuota creado exitosamente.")
        return redirect(self.get_success_url())

    def form_invalid(self, form, conceptos_formset):
        context = self.get_context_data(form=form, conceptos_formset=conceptos_formset)
        return self.render_to_response(context)

    def _get_complejo(self):
        """Helper para determinar el complejo basado en el usuario o el formulario."""
        if self.request.user.rol == 'GERENTE':
            return self.request.user.complejo_asignado
        if self.request.POST:
            complejo_id = self.request.POST.get('complejo')
            if complejo_id:
                return get_object_or_404(Complejo, id=complejo_id)
        return None

class PlanCuotaUpdateView(LoginRequiredMixin, UpdateView):
    model = PlanCuota
    form_class = PlanCuotaForm
    template_name = 'finanzas/editar_plan_cuota.html'
    success_url = reverse_lazy('lista_planes_cuota')

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.rol == 'ADMIN' or request.user.rol == 'GERENTE'):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['conceptos_formset'] = PlanConceptoCobroFormSet(self.request.POST, instance=self.object, form_kwargs={'complejo': self.object.complejo})
        else:
            data['conceptos_formset'] = PlanConceptoCobroFormSet(instance=self.object, form_kwargs={'complejo': self.object.complejo})
        return data

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        conceptos_formset = PlanConceptoCobroFormSet(request.POST, instance=self.object, form_kwargs={'complejo': self.object.complejo})

        if form.is_valid() and conceptos_formset.is_valid():
            return self.form_valid(form, conceptos_formset)
        else:
            return self.form_invalid(form, conceptos_formset)

    def form_valid(self, form, conceptos_formset):
        with transaction.atomic():
            self.object = form.save()
            conceptos_formset.instance = self.object
            conceptos_formset.save()

        messages.success(self.request, "Plan de cuota actualizado exitosamente.")
        return redirect(self.get_success_url())

    def form_invalid(self, form, conceptos_formset):
        context = self.get_context_data(form=form, conceptos_formset=conceptos_formset)
        return self.render_to_response(context)
        
    def get_queryset(self):
        user = self.request.user
        if user.rol == 'ADMIN':
            return PlanCuota.objects.all()
        elif user.rol == 'GERENTE' and user.complejo_asignado:
            return PlanCuota.objects.filter(complejo=user.complejo_asignado)
        return PlanCuota.objects.none()

# Vistas para ConceptoCobro
class ConceptoCobroListView(LoginRequiredMixin, ListView):
    model = ConceptoCobro
    template_name = 'finanzas/lista_conceptos_cobro.html'
    context_object_name = 'conceptos'

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.rol == 'ADMIN' or request.user.rol == 'GERENTE'):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'ADMIN':
            return ConceptoCobro.objects.all()
        elif user.rol == 'GERENTE' and user.complejo_asignado:
            return ConceptoCobro.objects.filter(complejo=user.complejo_asignado)
        return ConceptoCobro.objects.none()

class ConceptoCobroCreateView(LoginRequiredMixin, CreateView):
    model = ConceptoCobro
    form_class = ConceptoCobroForm
    template_name = 'finanzas/crear_concepto_cobro.html'
    success_url = reverse_lazy('lista_conceptos_cobro')

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.rol == 'ADMIN' or request.user.rol == 'GERENTE'):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        if self.request.user.rol == 'GERENTE' and self.request.user.complejo_asignado:
            form.instance.complejo = self.request.user.complejo_asignado
        return super().form_valid(form)

class ConceptoCobroUpdateView(LoginRequiredMixin, UpdateView):
    model = ConceptoCobro
    form_class = ConceptoCobroForm
    template_name = 'finanzas/editar_concepto_cobro.html'
    success_url = reverse_lazy('lista_conceptos_cobro')

    def dispatch(self, request, *args, **kwargs):
        if not (request.user.rol == 'ADMIN' or request.user.rol == 'GERENTE'):
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'ADMIN':
            return ConceptoCobro.objects.all()
        elif user.rol == 'GERENTE' and user.complejo_asignado:
            return ConceptoCobro.objects.filter(complejo=user.complejo_asignado)
        return ConceptoCobro.objects.none()

# Vistas para MetodoPago (Admin)
class MetodoPagoListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = MetodoPago
    template_name = 'finanzas/lista_metodos_pago.html'
    context_object_name = 'metodos'

class MetodoPagoCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = MetodoPago
    form_class = MetodoPagoForm
    template_name = 'finanzas/crear_metodo_pago.html'
    success_url = reverse_lazy('lista_metodos_pago')

class MetodoPagoUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = MetodoPago
    form_class = MetodoPagoForm
    template_name = 'finanzas/editar_metodo_pago.html'
    success_url = reverse_lazy('lista_metodos_pago')

# Vistas para Factura (Gerente)
class FacturaListView(LoginRequiredMixin, GerenteRequiredMixin, ListView):
    model = Factura
    template_name = 'finanzas/lista_facturas.html'
    context_object_name = 'facturas'

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'GERENTE':
            return Factura.objects.filter(propiedad__complejo=user.complejo_asignado)
        return Factura.objects.none()

class FacturaCreateView(LoginRequiredMixin, GerenteRequiredMixin, CreateView):
    model = Factura
    form_class = FacturaForm
    template_name = 'finanzas/crear_factura.html'
    success_url = reverse_lazy('lista_facturas')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['detalles'] = DetalleFacturaFormSet(self.request.POST)
        else:
            data['detalles'] = DetalleFacturaFormSet()
        return data

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        detalles_formset = DetalleFacturaFormSet(request.POST)

        if form.is_valid() and detalles_formset.is_valid():
            return self.form_valid(form, detalles_formset)
        else:
            return self.form_invalid(form, detalles_formset)

    def form_valid(self, form, detalles_formset):
        with transaction.atomic():
            # Guardar la factura principal
            factura = form.save(commit=False)
            # Asignar el usuario creador si tienes ese campo
            # factura.usuario_creador = self.request.user 
            factura.save()

            # Asociar y guardar los detalles
            detalles_formset.instance = factura
            detalles_formset.save()

        messages.success(self.request, "Factura creada exitosamente.")
        return redirect(self.get_success_url())

    def form_invalid(self, form, detalles_formset):
        # Pasar los formularios con errores de vuelta a la plantilla
        context = self.get_context_data(form=form, detalles=detalles_formset)
        return self.render_to_response(context)

class FacturaUpdateView(LoginRequiredMixin, GerenteRequiredMixin, UpdateView):
    model = Factura
    form_class = FacturaForm
    template_name = 'finanzas/editar_factura.html'
    success_url = reverse_lazy('lista_facturas')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['detalles'] = DetalleFacturaFormSet(self.request.POST, instance=self.object)
        else:
            data['detalles'] = DetalleFacturaFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        detalles = context['detalles']
        with transaction.atomic():
            self.object = form.save(commit=False)
            if detalles.is_valid():
                detalles.instance = self.object
                detalles.save()

                # Recalculate total from saved details for security
                total = sum(d.monto for d in self.object.detalles.all() if not d.get('_delete', False))

                self.object.save() # Save again with correct total
            else:
                return self.form_invalid(form)

        return super(FacturaUpdateView, self).form_valid(form)

class FacturaDetailView(LoginRequiredMixin, GerenteRequiredMixin, DetailView):
    model = Factura
    template_name = 'finanzas/factura_detail.html'
    context_object_name = 'factura'

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'GERENTE':
            return Factura.objects.filter(propiedad__complejo=user.complejo_asignado)
        elif user.rol == 'ADMIN':
            return Factura.objects.all()
        return Factura.objects.none()

# Vistas para Recaudo (Gerente)
class RecaudoCreateView(LoginRequiredMixin, GerenteRequiredMixin, CreateView):
    model = Recaudo
    form_class = RecaudoForm
    template_name = 'finanzas/crear_recaudo.html'
    success_url = reverse_lazy('lista_facturas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['factura'] = get_object_or_404(Factura, pk=self.kwargs['factura_pk'])
        return context

    def form_valid(self, form):
        factura = get_object_or_404(Factura, pk=self.kwargs['factura_pk'])
        recaudo = form.save(commit=False)
        recaudo.factura = factura
        recaudo.usuario_registro = self.request.user
        recaudo.save()

        return super().form_valid(form)

class ReporteCobranzaView(LoginRequiredMixin, GerenteRequiredMixin, ListView):
    model = Recaudo
    template_name = 'finanzas/reporte_cobranza.html'
    context_object_name = 'recaudos'

    def get_queryset(self):
        user = self.request.user
        if user.rol == 'GERENTE':
            return Recaudo.objects.filter(factura__propiedad__complejo=user.complejo_asignado).order_by('-fecha_pago')
        return Recaudo.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        total_recaudado = queryset.aggregate(total=models.Sum('monto_pagado'))['total'] or 0
        context['total_recaudado'] = total_recaudado
        return context

# Vistas para Residente
class MisFacturasView(LoginRequiredMixin, ResidenteRequiredMixin, ListView):
    model = Factura
    template_name = 'finanzas/mis_facturas.html'
    context_object_name = 'facturas'

    def get_queryset(self):
        return Factura.objects.filter(propiedad__residentes=self.request.user).order_by('-fecha_emision')

class GenerateInvoicesView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        if not (user.rol == 'ADMIN' or (user.rol == 'GERENTE' and user.complejo_asignado)):
            messages.error(request, 'No tienes permiso para generar facturas.')
            return redirect(reverse('dashboard')) # Redirect to dashboard or appropriate page

        # Determine which complex to process
        complejo_id = None
        if user.rol == 'GERENTE':
            complejo_id = user.complejo_asignado.id
        # If Admin, can either process all or specific complex via POST data if implemented

        output = StringIO()
        try:
            # Pass complejo_id to the management command if needed
            if complejo_id:
                call_command('generate_monthly_invoices', '--complejo_id', str(complejo_id), stdout=output)
            else: # Admin scenario, generate for all complexes for now
                call_command('generate_monthly_invoices', stdout=output)
            
            messages.success(request, f'Generación de facturas iniciada. Revise los resultados: {output.getvalue()}')
        except Exception as e:
            messages.error(request, f'Error al generar facturas: {e}')
        
        return redirect(reverse('lista_facturas'))

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

# Vistas para Recibo de Pago
class ReciboPagoView(LoginRequiredMixin, GerenteRequiredMixin, DetailView):
    model = Recaudo
    template_name = 'finanzas/recibo_pago.html'
    context_object_name = 'recaudo'

    def get_queryset(self):
        # Ensure only manager of the complex can see receipts for their complex
        user = self.request.user
        if user.rol == 'GERENTE' and user.complejo_asignado:
            return Recaudo.objects.filter(factura__propiedad__complejo=user.complejo_asignado)
        # Admins can see all receipts
        elif user.rol == 'ADMIN':
            return Recaudo.objects.all()
        return Recaudo.objects.none()

@login_required
def get_conceptos_plan(request):
    plan_id = request.GET.get('plan_id')
    if not plan_id:
        return JsonResponse({'error': 'No plan_id provided'}, status=400)
    
    try:
        plan = PlanCuota.objects.get(id=plan_id)
        conceptos = plan.planconceptocobro_set.all().select_related('concepto_cobro')
        
        conceptos_data = []
        for pcc in conceptos:
            conceptos_data.append({
                'id': pcc.concepto_cobro.id,
                'nombre': pcc.concepto_cobro.nombre,
                'monto': pcc.monto,
            })
            
        return JsonResponse({'conceptos': conceptos_data})
    except PlanCuota.DoesNotExist:
        return JsonResponse({'error': 'Plan not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

