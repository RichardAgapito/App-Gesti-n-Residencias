from django import forms
from django.forms import inlineformset_factory
from django.core.exceptions import ValidationError # Added
from django.utils import timezone # Added
from .models import PlanCuota, Factura, DetalleFactura, ConceptoCobro, MetodoPago, Recaudo, PlanConceptoCobro, ConfiguracionFinanciera
from complejos.models import Complejo, Propiedad # Import Complejo and Propiedad

class PlanCuotaForm(forms.ModelForm):
    class Meta:
        model = PlanCuota
        fields = ['nombre', 'descripcion', 'frecuencia', 'activo', 'complejo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'frecuencia': forms.Select(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'complejo': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            if user.rol == 'GERENTE':
                if user.complejo_asignado:
                    self.fields['complejo'].queryset = Complejo.objects.filter(id=user.complejo_asignado.id)
                    self.fields['complejo'].initial = user.complejo_asignado
                    self.fields['complejo'].widget = forms.HiddenInput()
                else: # Gerente without assigned complejo should not see this or get an error
                    self.fields['complejo'].widget = forms.HiddenInput()
                    self.fields['complejo'].required = False
            elif user.rol == 'ADMIN':
                self.fields['complejo'].queryset = Complejo.objects.all()
            else: # Other roles should not see this form, but for safety
                self.fields['complejo'].widget = forms.HiddenInput()
                self.fields['complejo'].required = False

class PlanConceptoCobroForm(forms.ModelForm):
    class Meta:
        model = PlanConceptoCobro
        fields = ['concepto_cobro', 'monto', 'orden']
        widgets = {
            'concepto_cobro': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'orden': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        complejo = kwargs.pop('complejo', None)
        super().__init__(*args, **kwargs)
        if complejo:
            self.fields['concepto_cobro'].queryset = ConceptoCobro.objects.filter(complejo=complejo)
        else:
            self.fields['concepto_cobro'].queryset = ConceptoCobro.objects.none()

PlanConceptoCobroFormSet = inlineformset_factory(
    PlanCuota,
    PlanConceptoCobro,
    form=PlanConceptoCobroForm,
    extra=1,
    can_delete=True,
    can_delete_extra=True
)

class ConceptoCobroForm(forms.ModelForm):
    class Meta:
        model = ConceptoCobro
        fields = ['nombre', 'descripcion', 'tipo', 'obligatorio', 'complejo'] # Added complejo
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'obligatorio': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'complejo': forms.Select(attrs={'class': 'form-control'}), # Added complejo widget
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            if user.rol == 'GERENTE':
                if user.complejo_asignado:
                    self.fields['complejo'].queryset = Complejo.objects.filter(id=user.complejo_asignado.id)
                    self.fields['complejo'].initial = user.complejo_asignado
                    self.fields['complejo'].widget = forms.HiddenInput()
                else:
                    self.fields['complejo'].widget = forms.HiddenInput()
                    self.fields['complejo'].required = False
            elif user.rol == 'ADMIN':
                self.fields['complejo'].queryset = Complejo.objects.all()
            else:
                self.fields['complejo'].widget = forms.HiddenInput()
                self.fields['complejo'].required = False

class MetodoPagoForm(forms.ModelForm):
    class Meta:
        model = MetodoPago
        fields = '__all__'
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'cuenta_banco': forms.TextInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'comision': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class FacturaForm(forms.ModelForm):
    class Meta:
        model = Factura
        fields = ['propiedad', 'plan_cuota', 'fecha_vencimiento', 'observaciones']
        widgets = {
            'propiedad': forms.Select(attrs={'class': 'form-control'}),
            'plan_cuota': forms.Select(attrs={'class': 'form-control'}),
            'fecha_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar el queryset de propiedades basado en el rol del usuario
        if user and user.rol == 'GERENTE':
            self.fields['propiedad'].queryset = self.fields['propiedad'].queryset.filter(complejo=user.complejo_asignado)
            
        # Hacer el plan de cuota opcional
        self.fields['plan_cuota'].required = False
        self.fields['plan_cuota'].label = "Plan de Cuota (Opcional, para autocompletar)"

class DetalleFacturaForm(forms.ModelForm):
    class Meta:
        model = DetalleFactura
        fields = ['concepto_cobro', 'monto', 'descripcion']
        widgets = {
            'concepto_cobro': forms.Select(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        complejo = kwargs.pop('complejo', None)
        super().__init__(*args, **kwargs)
        if complejo:
            self.fields['concepto_cobro'].queryset = ConceptoCobro.objects.filter(complejo=complejo)
        else:
            # If no complex provided (e.g. Admin view without specific filter, or early init), 
            # ideally show all or nothing. For Admin show all.
            # But wait, if I don't pass anything, it defaults to all.
            pass

DetalleFacturaFormSet = inlineformset_factory(
    Factura,
    DetalleFactura,
    form=DetalleFacturaForm,
    extra=1,
    can_delete=True,
    can_delete_extra=True
)

class RecaudoForm(forms.ModelForm):
    class Meta:
        model = Recaudo
        fields = ['fecha_pago', 'monto_pagado', 'metodo_pago', 'referencia', 'observaciones']
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'monto_pagado': forms.NumberInput(attrs={'class': 'form-control'}),
            'metodo_pago': forms.Select(attrs={'class': 'form-control'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        monto_pagado = cleaned_data.get('monto_pagado')
        fecha_pago = cleaned_data.get('fecha_pago')
        factura = self.instance.factura if self.instance else self.initial.get('factura') # Get factura from instance or initial data
        metodo_pago = cleaned_data.get('metodo_pago')
        referencia = cleaned_data.get('referencia')

        if monto_pagado is not None and monto_pagado <= 0:
            self.add_error('monto_pagado', 'El monto pagado debe ser mayor que cero.')

        if fecha_pago and fecha_pago > timezone.localdate():
            self.add_error('fecha_pago', 'La fecha de pago no puede ser futura.')

        if factura:
            if factura.estado not in ['PENDIENTE', 'VENCIDA']:
                self.add_error(None, f'No se puede registrar un pago para una factura en estado {factura.get_estado_display()}.')
            
            # Check for duplicate payments for the same invoice, amount, method, and reference within a reasonable timeframe (e.g., same day)
            # This is a basic check. A more robust solution might involve a unique_together constraint on the model
            # or a more complex deduplication logic.
            if Recaudo.objects.filter(
                factura=factura,
                monto_pagado=monto_pagado,
                metodo_pago=metodo_pago,
                referencia=referencia,
                fecha_pago=fecha_pago # Strict check, might need to be more flexible
            ).exclude(pk=self.instance.pk if self.instance else None).exists():
                self.add_error(None, 'Ya existe un pago con los mismos detalles para esta factura.')

        return cleaned_data



class ConfiguracionFinancieraForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionFinanciera
        fields = ['dia_corte', 'dias_vencimiento', 'tasa_interes_mora_diaria', 'bloquear_servicios_con_deuda', 'plan_mantenimiento_default']
        widgets = {
            'dia_corte': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 28, 'placeholder': 'Ej: 5'}),
            'dias_vencimiento': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 10'}),
            'tasa_interes_mora_diaria': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001', 'placeholder': 'Ej: 0.033'}),
            'bloquear_servicios_con_deuda': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'plan_mantenimiento_default': forms.Select(attrs={'class': 'form-control select2'}),
        }
        labels = {
            'dia_corte': 'Día del Mes de Corte',
            'dias_vencimiento': 'Días de Gracia',
            'tasa_interes_mora_diaria': 'Tasa de Interés por Mora Diaria (%)',
            'plan_mantenimiento_default': 'Plan de Cuotas Predeterminado (Gastos Comunes)',
        }
    
    def __init__(self, *args, **kwargs):
        complejo = kwargs.pop('complejo', None)
        super().__init__(*args, **kwargs)
        
        if complejo:
             self.fields['plan_mantenimiento_default'].queryset = PlanCuota.objects.filter(complejo=complejo, activo=True)
        else:
             self.fields['plan_mantenimiento_default'].queryset = PlanCuota.objects.none()

        # Force clear initial values only if it's a NEW instance (unsaved)
        # This ensures placeholders appear for new configs, but existing data remains editable.
        if not self.instance.pk:
            self.initial['dia_corte'] = None
            self.initial['dias_vencimiento'] = None
            self.initial['tasa_interes_mora_diaria'] = None

class ResidenteRecaudoForm(RecaudoForm):
    class Meta(RecaudoForm.Meta):
        fields = ['metodo_pago', 'referencia', 'monto_pagado', 'observaciones'] # Exclude fecha_pago
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter active payment methods only
        self.fields['metodo_pago'].queryset = MetodoPago.objects.filter(activo=True)
        self.fields['monto_pagado'].label = "Monto a Pagar"
        
        # Make monto_pagado read-only if you want to force full payment, 
        # or leave editable for partial payments. User request said "registre los datos", 
        # usually implies entering amount. We'll leave it editable but maybe pre-filled in View.
        
    def save(self, commit=True):
        recaudo = super().save(commit=False)
        recaudo.fecha_pago = timezone.localdate() # Always today for resident self-report
        if commit:
            recaudo.save()
        return recaudo
