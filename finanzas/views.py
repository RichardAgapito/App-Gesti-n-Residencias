from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, View, TemplateView, DetailView
from .models import PlanCuota, ConceptoCobro, MetodoPago, Factura, Recaudo, ConfiguracionFinanciera
from .forms import (
    PlanCuotaForm, ConceptoCobroForm, MetodoPagoForm, FacturaForm, 
    DetalleFacturaFormSet, RecaudoForm, PlanConceptoCobroFormSet,
    ConfiguracionFinancieraForm, ResidenteRecaudoForm
)
from django.db import transaction, models
from django.shortcuts import get_object_or_404, redirect, reverse
from django.http import Http404
from django.contrib import messages
from django.core.management import call_command
from django.core.management import call_command
from io import StringIO
from complejos.models import Complejo, PropiedadPersona # Added PropiedadPersona
from finanzas.models import ContratoFinanciero # Added ContratoFinanciero


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
        return self.request.user.is_authenticated and (self.request.user.rol == 'GERENTE' or self.request.user.rol == 'ADMIN')

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
            # Crea el objeto en memoria sin guardarlo aún en la BD
            self.object = form.save(commit=False)
            
            # Asigna el complejo para el Gerente
            if self.request.user.rol == 'GERENTE' and self.request.user.complejo_asignado:
                self.object.complejo = self.request.user.complejo_asignado
            
            # Ahora guarda el objeto principal
            self.object.save()
            
            # Asocia el objeto principal con el formset y guarda
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
        queryset = Factura.objects.select_related('propiedad__complejo', 'plan_cuota')

        if user.rol == 'ADMIN':
            # Start with all invoices for Admin
            queryset = queryset.all()
            
            # Get filter params
            complejo_id = self.request.GET.get('complejo')
            estado = self.request.GET.get('estado')

            if complejo_id:
                queryset = queryset.filter(propiedad__complejo__id=complejo_id)
            if estado:
                queryset = queryset.filter(estado=estado)

        elif user.rol == 'GERENTE':
            # Gerente can only see their own complex's invoices
            queryset = queryset.filter(propiedad__complejo=user.complejo_asignado)
            
            # They can also filter by status
            estado = self.request.GET.get('estado')
            if estado:
                queryset = queryset.filter(estado=estado)
        else:
            queryset = Factura.objects.none()

        return queryset.order_by('-fecha_emision') # Add ordering

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Add filter data to context for the template
        if user.rol == 'ADMIN':
            context['complejos'] = Complejo.objects.all()
            context['selected_complejo'] = self.request.GET.get('complejo', '')
        
        context['estados'] = Factura.Estado.choices
        context['selected_estado'] = self.request.GET.get('estado', '')
        return context

class FacturaCreateView(LoginRequiredMixin, GerenteRequiredMixin, CreateView):
    model = Factura
    form_class = FacturaForm
    template_name = 'finanzas/crear_factura.html'
    success_url = reverse_lazy('lista_facturas')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.rol != 'GERENTE':
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data['detalles'] = DetalleFacturaFormSet(self.request.POST, form_kwargs={'complejo': self.request.user.complejo_asignado})
        else:
            data['detalles'] = DetalleFacturaFormSet(form_kwargs={'complejo': self.request.user.complejo_asignado})
        return data

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        detalles = DetalleFacturaFormSet(request.POST, form_kwargs={'complejo': self.request.user.complejo_asignado})
        
        if form.is_valid() and detalles.is_valid():
            return self.form_valid(form, detalles)
        else:
            return self.form_invalid(form, detalles)

    def form_valid(self, form, detalles):
        with transaction.atomic():
            # 1. Save the main Invoice
            self.object = form.save()
            
            # 2. Save Manual Details
            detalles.instance = self.object
            detalles.save()

            # 3. Automatic Generation Logic (ONLY if Plan is selected)
            # We respect the user's choice: If plan_cuota is None, we treat this as a purely manual invoice.
            if self.object.plan_cuota:
                plan_efectivo = self.object.plan_cuota
                
                # A. Generate Standard Details from Plan
                from .models import DetalleFactura # Avoid circular import if any
                conceptos_plan = plan_efectivo.planconceptocobro_set.all()
                for pcc in conceptos_plan:
                    DetalleFactura.objects.create(
                        factura=self.object,
                        concepto_cobro=pcc.concepto_cobro,
                        monto=pcc.monto,
                        descripcion=pcc.concepto_cobro.nombre
                    )

                # B. Generate Financing Details (Mortgage) if applicable
                # We need to find the Financial Contract associated with this property
                contrato = PropiedadPersona.objects.filter(
                    propiedad=self.object.propiedad,
                    estado='activo'
                ).first()

                if contrato:
                    try:
                        contrato_financiero = contrato.contrato_financiero
                        # Logic: If there is a pending amount and cuotas remaining
                        if contrato_financiero.monto_pendiente and contrato_financiero.monto_pendiente > 0:
                            if contrato_financiero.numero_cuotas_totales and contrato_financiero.numero_cuotas_totales > contrato_financiero.cuotas_facturadas:
                                cuotas_restantes = contrato_financiero.numero_cuotas_totales - contrato_financiero.cuotas_facturadas
                                monto_cuota = contrato_financiero.monto_pendiente / cuotas_restantes
                                
                                numero_cuota_actual = contrato_financiero.cuotas_facturadas + 1
                                
                                DetalleFactura.objects.create(
                                    factura=self.object,
                                    monto=monto_cuota,
                                    descripcion=f"Cuota de Financiamiento ({numero_cuota_actual}/{contrato_financiero.numero_cuotas_totales})"
                                )
                                
                                # Update Contract State
                                contrato_financiero.cuotas_facturadas += 1
                                contrato_financiero.save()
                    except ContratoFinanciero.DoesNotExist:
                        pass
            
            if not self.object.plan_cuota and not detalles.has_changed() and not detalles.initial_form_count() > 0:
                 # Logic check: If no plan and no details were added manually
                 messages.warning(self.request, "Se creó una factura sin conceptos (ni automáticos ni manuales).")

        messages.success(self.request, "Factura creada exitosamente.")
        return redirect(self.get_success_url())

    def form_invalid(self, form, detalles):
        return self.render_to_response(self.get_context_data(form=form, detalles=detalles))

class FacturaUpdateView(LoginRequiredMixin, GerenteRequiredMixin, UpdateView):
    model = Factura
    form_class = FacturaForm
    template_name = 'finanzas/editar_factura.html'
    success_url = reverse_lazy('lista_facturas')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.rol != 'GERENTE':
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)

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

class MisFacturasView(LoginRequiredMixin, ResidenteRequiredMixin, ListView):
    model = Factura
    template_name = 'finanzas/mis_facturas.html'
    context_object_name = 'facturas'

    def get_queryset(self):
        # Traemos las facturas con sus detalles pre-cargados para no matar la base de datos
        return Factura.objects.filter(
            propiedad__residentes=self.request.user
        ).order_by('-fecha_emision').prefetch_related('detalles', 'detalles__concepto_cobro')

class RegistrarPagoResidenteView(LoginRequiredMixin, ResidenteRequiredMixin, CreateView):
    model = Recaudo
    form_class = ResidenteRecaudoForm
    template_name = 'finanzas/registrar_pago_residente.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        factura = get_object_or_404(Factura, pk=self.kwargs['pk'], propiedad__residentes=self.request.user)
        context['factura'] = factura
        return context

    def get_initial(self):
        initial = super().get_initial()
        factura = get_object_or_404(Factura, pk=self.kwargs['pk'], propiedad__residentes=self.request.user)
        initial['monto_pagado'] = factura.saldo_pendiente
        return initial

    def form_valid(self, form):
        factura = get_object_or_404(Factura, pk=self.kwargs['pk'], propiedad__residentes=self.request.user)
        if factura.estado == 'PAGADA':
             form.add_error(None, "Esta factura ya está pagada.")
             return self.form_invalid(form)
             
        recaudo = form.save(commit=False)
        recaudo.factura = factura
        recaudo.usuario_registro = self.request.user
        recaudo.save()
        messages.success(self.request, "Pago registrado correctamente. Queda pendiente de validación.")
        return redirect('mis_facturas')

class FacturaDetalleResidenteView(LoginRequiredMixin, ResidenteRequiredMixin, DetailView):
    model = Factura
    template_name = 'finanzas/detalle_factura_residente.html'
    context_object_name = 'factura'

    def get_queryset(self):
        return Factura.objects.filter(propiedad__residentes=self.request.user)
    success_url = reverse_lazy('mis_facturas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['factura'] = get_object_or_404(Factura, pk=self.kwargs['pk'], propiedad__residentes=self.request.user)
        return context

    def get_initial(self):
        initial = super().get_initial()
        factura = get_object_or_404(Factura, pk=self.kwargs['pk'], propiedad__residentes=self.request.user)
        initial['monto_pagado'] = factura.saldo_pendiente # Pre-fill with pending amount
        return initial

    def form_valid(self, form):
        factura = get_object_or_404(Factura, pk=self.kwargs['pk'], propiedad__residentes=self.request.user)
        
        if factura.estado == 'PAGADA':
             messages.error(self.request, "Esta factura ya está pagada.")
             return redirect('mis_facturas')

        recaudo = form.save(commit=False)
        recaudo.factura = factura
        recaudo.usuario_registro = self.request.user
        recaudo.save()
        
        # Trigger any status update logic if needed (handled by signal/save usually)
        
        messages.success(self.request, "Pago registrado exitosamente. Será validado por la administración.")
        return super().form_valid(form)
        
class UpdateFinancialStatusView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        # Validación de permisos: Solo ADMIN o GERENTE
        user = request.user
        if not (user.rol == 'ADMIN' or (user.rol == 'GERENTE' and user.complejo_asignado)):
            messages.error(request, 'No tienes permiso para actualizar estados financieros.')
            return redirect(reverse('dashboard'))

        output = StringIO()
        try:
            # Ejecutamos el comando que acabamos de crear
            call_command('update_financial_status', stdout=output)
            
            messages.success(request, f'Actualización completada. Resultados: {output.getvalue()}')
        except Exception as e:
            messages.error(request, f'Error al actualizar estados: {e}')
        
        # Redirigimos a la misma lista de facturas para ver los cambios (ej. estados VENCIDA)
        # Redirigimos a la misma lista de facturas para ver los cambios (ej. estados VENCIDA)
        return redirect(reverse('lista_facturas'))



class ConfiguracionFinancieraUpdateView(LoginRequiredMixin, GerenteRequiredMixin, UpdateView):
    model = ConfiguracionFinanciera
    form_class = ConfiguracionFinancieraForm
    template_name = 'finanzas/configuracion_financiera.html'
    success_url = reverse_lazy('configuracion_financiera')

    def get_object(self, queryset=None):
        user = self.request.user
        complejo = user.complejo_asignado

        # Admin logic: Check for 'complejo_id' in GET or use assigned complex
        if not complejo and (user.rol == 'ADMIN' or user.is_superuser):
            complejo_id = self.request.GET.get('complejo_id')
            if complejo_id:
                complejo = get_object_or_404(Complejo, id=complejo_id)
            else:
                # If Admin and no complex specified, we can't show config.
                # Returning None here might crash UpdateView.
                # We should handle this in dispatch or redirect earlier.
                # However, raising 404 is standard, but we want to prompt selection.
                # Let's rely on the dispatch override below or just None (handled below).
                return None

        if not complejo:
             # Should be caught by dispatch/redirect, but if here:
             raise Http404("No tienes un complejo asignado.")
        
        try:
            return ConfiguracionFinanciera.objects.get(complejo=complejo, propiedad=None)
        except ConfiguracionFinanciera.DoesNotExist:
            # Return a new, unsaved instance preventing premature DB creation
            return ConfiguracionFinanciera(complejo=complejo)

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if not user.complejo_asignado and (user.rol == 'ADMIN' or user.is_superuser):
            if not request.GET.get('complejo_id'):
                return redirect('seleccionar_complejo_finanzas')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Ensure we pass the correct complex to the form
        if self.object:
            kwargs['complejo'] = self.object.complejo
        else:
             # Fallback if object creation failed (shouldn't happen with redirect)
             kwargs['complejo'] = self.request.user.complejo_asignado
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Configuración financiera actualizada correctamente.")
        # Preserve complejo_id in success URL if needed
        response = super().form_valid(form)
        if 'complejo_id' in self.request.GET:
             self.success_url = f"{reverse_lazy('configuracion_financiera')}?complejo_id={self.request.GET['complejo_id']}"
        return response

class SeleccionarComplejoFinanzasView(LoginRequiredMixin, ListView):
    model = Complejo
    template_name = 'finanzas/seleccionar_complejo.html'
    context_object_name = 'complejos'

    def get_queryset(self):
        return Complejo.objects.filter(estado='activo')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Seleccionar Complejo para Configuración"
        return context

@login_required
def get_conceptos_contrato(request):
    """
    Devuelve los conceptos de cobro (nombre, id, monto) aplicables a una propiedad
    basándose en su ContratoFinanciero activo.
    Prioridad:
    1. Plan Personalizado (si contrato.contrato_financiero.plan existe)
    2. Plan Default del Complejo (ConfiguracionFinanciera)
    """
    propiedad_id = request.GET.get('propiedad_id')
    if not propiedad_id:
        return JsonResponse({'error': 'No propiedad_id provided'}, status=400)
    
    try:
        # 1. Buscar contrato activo
        contrato = PropiedadPersona.objects.filter(
            propiedad_id=propiedad_id,
            estado='activo'
        ).first()

        if not contrato:
            return JsonResponse({'error': 'No active contract found for this property'}, status=404)

        # 2. Buscar ContratoFinanciero
        # OJO: Puede que no exista si no se creó. Asumimos que debería existir si hay contrato activo.
        # Si no, fallamos suavemente o buscamos defaults puros.
        try:
            contrato_financiero = contrato.contrato_financiero
        except ContratoFinanciero.DoesNotExist:
             return JsonResponse({'error': 'No financial contract found'}, status=404)

        # 3. Determinar Plan Efectivo
        plan = None
        if contrato_financiero.plan:
            plan = contrato_financiero.plan
        # else:
            # No fallback to default configuration logic
        # REVERTED ABOVE: We DO recognize default if no specific plan.
        if not plan: # Only if no personalized plan
            config = ConfiguracionFinanciera.objects.filter(complejo=contrato.propiedad.complejo).first()
            if config:
                plan = config.plan_mantenimiento_default
        
        conceptos_data = []

        if plan:
            # Cargar conceptos del plan
            conceptos = plan.planconceptocobro_set.all().select_related('concepto_cobro')
            for pcc in conceptos:
                conceptos_data.append({
                    'id': pcc.concepto_cobro.id,
                    'nombre': pcc.concepto_cobro.nombre,
                    'monto': float(pcc.monto), # Decimal to float for JSON
                    'tipo': 'Plan'
                })
        else:
             # Fallback final: Si no hay plan ni default, tal vez devolver vacío o error.
             # Por ahora vacío.
             pass

        return JsonResponse({
            'conceptos': conceptos_data,
            'plan_id': plan.id if plan else None,
            'plan_nombre': plan.nombre if plan else None
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
