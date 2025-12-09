
import os
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from complejos.models import PropiedadPersona, Propiedad, Complejo, Amenidad
from finanzas.models import ContratoFinanciero, ConceptoCobro, PlanCuota, PlanConceptoCobro
from users.models import CustomUser
from django.test import RequestFactory
from complejos.views import editar_contrato
from django.contrib.messages.storage.fallback import FallbackStorage

def setup_test_data():
    print("Setting up test data...")
    # Users
    user, _ = CustomUser.objects.get_or_create(email="test_edit_contract@example.com", defaults={'rol': 'RESIDENTE'})
    admin, _ = CustomUser.objects.get_or_create(email="admin_edit@example.com", defaults={'rol': 'ADMIN', 'is_superuser': True})
    
    # Conceptos
    c_alquiler, _ = ConceptoCobro.objects.get_or_create(nombre="Alquiler Test", defaults={'tipo': 'ORDINARIO'})
    c_mantenimiento, _ = ConceptoCobro.objects.get_or_create(nombre="Mantenimiento Test", defaults={'tipo': 'ORDINARIO'})
    
    # Contract
    # Mock Objects for minimal dependency
    complejo, _ = Complejo.objects.get_or_create(
        nombre="Complejo Test Edit", 
        defaults={
            'calle': 'Test Calle',
            'ciudad': 'Test Ciudad',
            'codigo_postal': '12345',
            'tipo': 'residencial',
            'numero_total_unidades': 10,
            'administrador_responsable': 'Test Admin',
            'telefono_contacto': '123456789'
        }
    )
    propiedad, _ = Propiedad.objects.get_or_create(
        complejo=complejo, 
        numero_identificador="TEST-101", 
        defaults={
            'tipo': 'casa',
            'area': 100,
            'numero_habitaciones': 3,
            'numero_banos': 2,
            'piso_nivel': 1,
            'valor_estimado': 100000,
            'estado_ocupacion': 'disponible'
        }
    )
    
    contrato, created = PropiedadPersona.objects.get_or_create(
        propiedad=propiedad,
        persona=user,
        defaults={
            'tipo_relacion': 'inquilino',
            'fecha_inicio': date.today(),
            'estado': 'activo'
        }
    )
    
    # Finanzas
    cf, _ = ContratoFinanciero.objects.get_or_create(propiedad_persona=contrato, defaults={'fecha_inicio_pago': date.today()})
    
    # Initial Concepts (via PlanCuota)
    if not cf.plan:
        plan = PlanCuota.objects.create(
            nombre=f"Plan Test {contrato.id}",
            complejo=complejo,
            activo=True
        )
        cf.plan = plan
        cf.save()
    
    # Reset items
    PlanConceptoCobro.objects.filter(plan_cuota=cf.plan).delete()
    PlanConceptoCobro.objects.create(plan_cuota=cf.plan, concepto_cobro=c_alquiler, monto=1000, orden=1)
    
    print(f"Contract {contrato.id} created/fetched with initial concept Alquiler=$1000 via Plan {cf.plan.id}")
    
    return contrato, admin, c_alquiler, c_mantenimiento

def test_edit_contract_logic():
    contrato, admin, c_alquiler, c_mantenimiento = setup_test_data()
    
    factory = RequestFactory()
    
    # Prepare POST data
    # We want to:
    # 1. Update existing Alquiler amount to 1200
    # 2. Add Mantenimiento at 150
    # 3. Set Custom Config to True with specific overrides
    
    data = {
        'fecha_fin': '', # Optional
        'estado': 'activo',
        
        # Financial Config Overrides (Now independent of concept creation)
        'configuracion_personalizada': 'on', # Checkbox
        'finanzas_dia_corte': '5',
        'finanzas_dias_vencimiento': '10',
        'finanzas_tasa_mora': '2.5',
        'finanzas_bloqueo': 'on',
        
        # Concepts (Dynamic list)
        'concepto_cobro_id': [str(c_alquiler.id), str(c_mantenimiento.id)],
        'concepto_monto': ['1200.00', '150.00']
    }
    
    print("Simulating POST request to editar_contrato...")
    request = factory.post(f'/complejos/contratos/{contrato.id}/editar/', data)
    request.user = admin
    
    # Add messages support
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    # Call View
    response = editar_contrato(request, contrato.id)
    
    # Check Result
    print(f"Response Status: {response.status_code}")
    if response.status_code != 302:
        print("Error: Expected redirect (302).")
        return

    # Verify Database Updates
    contrato.refresh_from_db()
    cf = contrato.contrato_financiero
    
    print("\nVerifying Financial Config:")
    print(f"Config Personalizada: {cf.configuracion_personalizada} (Expected True)")
    
    assert cf.configuracion_personalizada == True
    assert cf.configuracion is not None
    print(f"Config Object: {cf.configuracion}")
    
    # Check fields on the config object
    print(f"Dia Corte: {cf.configuracion.dia_corte} (Expected 5)")
    print(f"Dias Vencimiento: {cf.configuracion.dias_vencimiento} (Expected 10)")
    print(f"Tasa Mora: {cf.configuracion.tasa_interes_mora_diaria} (Expected 2.50)")
    
    assert cf.configuracion.dia_corte == 5
    assert cf.configuracion.dias_vencimiento == 10
    # Note: Decimal comparison might need exact type match or string
    assert cf.configuracion.tasa_interes_mora_diaria == Decimal('2.50')
    
    print("\nVerifying Concepts via PlanCuota:")
    assert cf.plan is not None
    
    conceptos = PlanConceptoCobro.objects.filter(plan_cuota=cf.plan).order_by('orden')
    for c in conceptos:
        print(f"- {c.concepto_cobro.nombre}: ${c.monto}")
        
    assert conceptos.count() == 2
    assert conceptos[0].concepto_cobro == c_alquiler
    assert conceptos[0].monto == Decimal('1200.00')
    assert conceptos[1].concepto_cobro == c_mantenimiento
    assert conceptos[1].monto == Decimal('150.00')
    
    print("\nSUCCESS: Contract Edit Logic Verified!")

if __name__ == "__main__":
    try:
        test_edit_contract_logic()
    except Exception as e:
        print(f"\nFAILED: {e}")
        import traceback
        traceback.print_exc()
