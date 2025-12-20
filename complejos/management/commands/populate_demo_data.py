import random
from datetime import date, datetime, timedelta, time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from faker import Faker

from complejos.models import Complejo, Amenidad, Propiedad, PropiedadPersona
from users.models import Persona, CustomUser
from finanzas.models import (
    ConceptoCobro, PlanCuota, PlanConceptoCobro, 
    ConfiguracionFinanciera, ContratoFinanciero,
    Factura, DetalleFactura, MetodoPago, Recaudo
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Popula la base de datos con datos de prueba (Complejos, Residentes, Finanzas)'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('Iniciando población de datos...'))
        fake = Faker('es_ES')

        # 1. Crear Superusuario
        if not User.objects.filter(email='admin@example.com').exists():
            persona_admin = Persona.objects.create(
                tipo_documento='DNI',
                numero_documento='00000001',
                nombres='Admin',
                apellidos='Principal',
                telefono='999999999',
                fecha_nacimiento=date(1990, 1, 1)
            )
            User.objects.create_superuser(
                email='admin@example.com',
                password='admin123',
                persona=persona_admin,
                rol=CustomUser.Rol.ADMIN
            )
            self.stdout.write(self.style.SUCCESS('Superusuario creado: admin@example.com / admin123'))

        # 2. Metodos de Pago
        metodo_transf, _ = MetodoPago.objects.get_or_create(
            nombre="Transferencia BCP",
            defaults={
                'tipo': 'TRANSFERENCIA',
                'banco': 'BCP',
                'numero_cuenta': '193-12345678-0-99',
                'activo': True
            }
        )

        # 3. Crear Amenidades
        amenidades_nombres = ['Piscina', 'Gimnasio', 'Zona de Parrillas', 'Salón de Eventos', 'Cancha de Tenis']
        amenidades_objs = []
        for nombre in amenidades_nombres:
            am, _ = Amenidad.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'descripcion': f'Area común para {nombre}',
                    'capacidad': random.randint(10, 50),
                    'hora_inicio': time(6, 0),
                    'hora_fin': time(22, 0)
                }
            )
            amenidades_objs.append(am)
        self.stdout.write(self.style.SUCCESS(f'Amenidades creadas: {len(amenidades_objs)}'))

        # 4. Datos Financieros Base (Conceptos - Precios en Soles más realistas)
        conceptos_base = [
            {'nombre': 'Cuota de Mantenimiento', 'tipo': 'ORDINARIO', 'monto': 150.00},
            {'nombre': 'Seguridad y Vigilancia', 'tipo': 'ORDINARIO', 'monto': 50.00},
            {'nombre': 'Agua Potable', 'tipo': 'ORDINARIO', 'monto': 20.00},
            {'nombre': 'Jardinería', 'tipo': 'ORDINARIO', 'monto': 15.00},
        ]
        
        # 5. Crear Complejos
        complejos_data = [
            {'nombre': 'Residencial Los Alamos', 'tipo': 'residencial', 'unidades': 20},
            {'nombre': 'Condominio El Sol', 'tipo': 'condominio', 'unidades': 20},
        ]

        # Fechas simuladas (Hace 1 mes para probar mora)
        fecha_inicio_contratos = date(2024, 11, 1)
        
        for idx_comp, c_data in enumerate(complejos_data):
            complejo = Complejo.objects.create(
                nombre=c_data['nombre'],
                calle=fake.street_address(),
                ciudad=fake.city(),
                codigo_postal=fake.postcode(),
                tipo=c_data['tipo'],
                numero_total_unidades=c_data['unidades'],
                telefono_contacto=f'9{random.randint(10000000, 99999999)}'
            )
            complejo.amenidades.set(random.sample(amenidades_objs, 3))
            
            # 5.1 Crear Configuración Financiera para este Complejo
            # Conceptos
            conceptos_objs = []
            for c_def in conceptos_base:
                concepto, _ = ConceptoCobro.objects.get_or_create(
                    nombre=c_def['nombre'],
                    tipo=c_def['tipo'],
                    complejo=complejo,
                    defaults={'obligatorio': True}
                )
                conceptos_objs.append({'obj': concepto, 'monto': c_def['monto']})

            # Plan de Cuotas Default
            plan_default = PlanCuota.objects.create(
                nombre=f'Plan Mantenimiento 2024 - {complejo.nombre}',
                descripcion='Plan estándar de mantenimiento',
                frecuencia='M',
                complejo=complejo
            )
            
            # Asignar conceptos al plan
            for i, item in enumerate(conceptos_objs):
                PlanConceptoCobro.objects.create(
                    plan_cuota=plan_default,
                    concepto_cobro=item['obj'],
                    monto=item['monto'],
                    orden=i+1
                )

            # Configuración Financiera
            ConfiguracionFinanciera.objects.create(
                nombre=f'Configuración General {complejo.nombre}',
                complejo=complejo,
                dia_corte=1, # Corte el 1 de cada mes
                dias_vencimiento=5, # Vence el 5
                tasa_interes_mora_diaria=0.033,
                bloquear_servicios_con_deuda=True,
                plan_mantenimiento_default=plan_default
            )

            # 5.2 Crear Gerente
            persona_gerente = Persona.objects.create(
                tipo_documento='DNI',
                numero_documento=f'1000000{idx_comp}',
                nombres=f'Gerente {idx_comp+1}',
                apellidos=fake.last_name(),
                telefono=f'9{random.randint(10000000, 99999999)}',
                fecha_nacimiento=fake.date_of_birth(minimum_age=30, maximum_age=60)
            )
            User.objects.create_user(
                email=f'gerente{idx_comp+1}@example.com',
                password='gerente123',
                persona=persona_gerente,
                rol=CustomUser.Rol.GERENTE,
                complejo_asignado=complejo
            )
            self.stdout.write(f"  > Gerente creado para {complejo.nombre}")

            # 5.3 Crear Propiedades y Residentes (5 por complejo)
            # SCENARIOS:
            # 0, 1: Alquiler, Mora
            # 2: Financiamiento (Compra), Pagado
            # 3: Alquiler, Pagado
            # 4: Alquiler, Mora
            for i in range(5):
                num_prop = f"P-{100+i}" if complejo.tipo == 'residencial' else f"D-{200+i}"
                propiedad = Propiedad.objects.create(
                    complejo=complejo,
                    numero_identificador=num_prop,
                    tipo='casa' if complejo.tipo == 'residencial' else 'departamento',
                    area=random.randint(60, 200),
                    numero_habitaciones=random.randint(1, 4),
                    numero_banos=random.randint(1, 3),
                    piso_nivel=str(random.randint(1, 5)),
                    valor_estimado=random.randint(100000, 500000),
                    estado_ocupacion='ocupado'
                )

                # Crear Residente
                dni_res = f'200{idx_comp}{i:04d}'
                persona_res = Persona.objects.create(
                    tipo_documento='DNI',
                    numero_documento=dni_res,
                    nombres=fake.first_name(),
                    apellidos=fake.last_name(),
                    telefono=f'9{random.randint(10000000, 99999999)}',
                    fecha_nacimiento=fake.date_of_birth(minimum_age=20, maximum_age=70)
                )
                
                email_res = f'residente{idx_comp+1}_{i+1}@example.com' # residente1_1@example.com
                usuario_res = User.objects.create_user(
                    email=email_res,
                    password='residente123',
                    persona=persona_res,
                    rol=CustomUser.Rol.RESIDENTE
                )
                
                # Crear Contrato
                pp = PropiedadPersona.objects.create(
                    propiedad=propiedad,
                    persona=usuario_res,
                    tipo_relacion='propietario',
                    porcentaje_propiedad=100.00,
                    fecha_inicio=fecha_inicio_contratos, # 2024-11-01
                    es_principal=True,
                    estado='activo'
                )

                # Definir Escenario
                es_financiamiento = (i == 2)
                esta_pagado = (i == 2 or i == 3) # Residentes 3 y 4 pagan

                # Crear Contrato Financiero
                cf = ContratoFinanciero.objects.create(
                    propiedad_persona=pp,
                    tipo='FINANCIAMIENTO' if es_financiamiento else 'ALQUILER',
                    estado='ACTIVO',
                    configuracion_personalizada=False,
                    fecha_inicio_pago=fecha_inicio_contratos, # 2024-11-01
                    adelanto=5000 if es_financiamiento else 0,
                    monto_cuota=1200.00 if es_financiamiento else None,
                    numero_cuotas_totales=60 if es_financiamiento else None,
                    cuotas_facturadas=0,
                    monto_pendiente=72000.00 if es_financiamiento else 0
                )

                self.stdout.write(f"    - Residente {email_res}: {cf.tipo}, Pagado? {esta_pagado}")

                # 4.4 GENERAR FACTURA DE NOVIEMBRE
                fecha_emision_nov = fecha_inicio_contratos
                fecha_vencimiento_nov = fecha_emision_nov + timedelta(days=5) # Vence el 5 Nov
                
                # Estado inicial: Si está pagado -> VENCIDA (pero luego se paga) o PENDIENTE -> PAGADA
                # Para simplificar, creamos como VENCIDA y luego si pagamos pasa a PAGADA
                estado_inicial = 'VENCIDA' 

                factura = Factura.objects.create(
                    propiedad=propiedad,
                    plan_cuota=plan_default,
                    contrato=cf,
                    fecha_emision=fecha_emision_nov,
                    fecha_vencimiento=fecha_vencimiento_nov,
                    estado=estado_inicial,
                    observaciones=f"Facturación Mensual - Noviembre 2024"
                )
                
                total_factura = 0

                # Detalles Base (Mantenimiento)
                for item in conceptos_objs:
                    DetalleFactura.objects.create(
                        factura=factura,
                        concepto_cobro=item['obj'],
                        monto=item['monto'],
                        descripcion="Cargo del periodo"
                    )
                    total_factura += float(item['monto'])
                
                # Detalle Cuota Financiamiento (si aplica)
                if es_financiamiento:
                    concepto_cuota, _ = ConceptoCobro.objects.get_or_create(
                        nombre="Cuota Financiamiento",
                        complejo=complejo,
                        defaults={'tipo': 'ORDINARIO'}
                    )
                    DetalleFactura.objects.create(
                        factura=factura,
                        concepto_cobro=concepto_cuota,
                        monto=cf.monto_cuota,
                        descripcion="Cuota 1/60"
                    )
                    total_factura += float(cf.monto_cuota)
                    cf.cuotas_facturadas += 1
                    cf.save()

                # Si el escenario es PAGADO, creamos el recaudo
                if esta_pagado:
                    Recaudo.objects.create(
                        factura=factura,
                        metodo_pago=metodo_transf,
                        fecha_pago=fecha_vencimiento_nov, # Pagó el mismo día de vencimieto (a tiempo)
                        monto_pagado=total_factura,
                        estado='APROBADO',
                        numero_operacion=f"OP-{random.randint(10000,99999)}",
                        usuario_registro=User.objects.get(email='admin@example.com')
                    )
                    # Forzamos update (aunque el modelo lo hace, aseguramos)
                    factura.estado = 'PAGADA'
                    factura.save()
                    self.stdout.write(f"      -> Factura {factura.numero_factura} PAGADA (${total_factura})")
                else:
                    self.stdout.write(f"      -> Factura {factura.numero_factura} VENCIDA, lista para Mora (${total_factura})")

        self.stdout.write(self.style.SUCCESS('\n¡Datos pobladados exitosamente!'))
        self.stdout.write(self.style.SUCCESS('Usuarios con deuda (Mora): residente1_1, residente1_2, residente1_5...'))
        self.stdout.write(self.style.SUCCESS('Usuarios al día: residente1_3 (Financ.), residente1_4...'))
