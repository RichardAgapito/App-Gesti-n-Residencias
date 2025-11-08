import random
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from users.models import CustomUser, Persona
from complejos.models import Complejo, Propiedad, Amenidad, Reserva, PropiedadPersona
from avisos.models import Aviso
from visitas.models import Visitante, Visita, PreAutorizacion

class Command(BaseCommand):
    help = 'Populate the database with realistic dummy data. WARNING: This will delete all existing data.'

    @transaction.atomic
    def handle(self, *args, **options):
        confirm = input(
            '\n'.join([
                'WARNING: This command will delete all data from the database.',
                'Are you sure you want to continue? (yes/no) [no]: '
            ])
        )
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Database population cancelled.'))
            return

        self.stdout.write(self.style.WARNING('Deleting existing data...'))
        # Clean up in reverse order of creation
        Visita.objects.all().delete()
        PreAutorizacion.objects.all().delete()
        Visitante.objects.all().delete()
        Aviso.objects.all().delete()
        Reserva.objects.all().delete()
        PropiedadPersona.objects.all().delete()
        Propiedad.objects.all().delete()
        Complejo.objects.all().delete()
        CustomUser.objects.all().delete()
        Persona.objects.all().delete()
        Amenidad.objects.all().delete()

        self.stdout.write(self.style.SUCCESS('Existing data deleted.'))
        self.stdout.write('Starting to populate the database...')

        fake = Faker('es_ES')

        # --- 1. Create Amenidades ---
        amenidades_nombres = ['Piscina', 'Gimnasio', 'Salón de Eventos', 'Cancha de Tenis', 'Área de Barbacoa']
        amenidades = []
        for nombre in amenidades_nombres:
            amenidad = Amenidad.objects.create(
                nombre=nombre,
                descripcion=fake.sentence(nb_words=10),
                capacidad=random.randint(5, 50),
                hora_inicio=datetime.time(8, 0),
                hora_fin=datetime.time(22, 0)
            )
            amenidades.append(amenidad)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(amenidades)} Amenidades.'))

        # --- 2. Create Complejos ---
        complejos = []
        for _ in range(3):
            complejo = Complejo.objects.create(
                nombre=f'Residencial {fake.last_name()}',
                calle=fake.street_address(),
                ciudad=fake.city(),
                codigo_postal=fake.postcode(),
                tipo=random.choice(['residencial', 'condominio']),
                numero_total_unidades=50,
                administrador_responsable=fake.name(),
                telefono_contacto=fake.numerify(text='9########')
            )
            complejo.amenidades.set(random.sample(amenidades, k=random.randint(2, 4)))
            complejos.append(complejo)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(complejos)} Complejos.'))

        # --- 3. Create Users (Superuser, Staff, Residents) ---
        super_persona = Persona.objects.create(
            nombres='Admin', 
            apellidos='Principal', 
            tipo_documento='DNI',
            numero_documento=fake.unique.numerify(text='########'), 
            telefono=fake.numerify(text='9########'),
            fecha_nacimiento=fake.date_of_birth(minimum_age=30, maximum_age=60)
        )
        superuser = CustomUser.objects.create_superuser(email='admin@example.com', password='adminpassword', persona=super_persona)
        self.stdout.write(self.style.SUCCESS('✓ Created Superuser (admin@example.com).'))

        staff_users = []
        for complejo in complejos:
            staff_persona = Persona.objects.create(
                nombres=fake.first_name(), 
                apellidos=fake.last_name(), 
                tipo_documento='DNI',
                numero_documento=fake.unique.numerify(text='########'), 
                telefono=fake.numerify(text='9########'),
                fecha_nacimiento=fake.date_of_birth(minimum_age=25, maximum_age=55)
            )
            staff_user = CustomUser.objects.create_user(
                email=f'staff_{complejo.nombre.split()[1].lower()}@example.com',
                password='staffpassword',
                persona=staff_persona,
                is_staff=True,
                complejo_asignado=complejo
            )
            staff_users.append(staff_user)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(staff_users)} Staff Users.'))

        resident_users = []
        for i in range(30):
            res_persona = Persona.objects.create(
                nombres=fake.first_name(), 
                apellidos=fake.last_name(), 
                tipo_documento='DNI',
                numero_documento=fake.unique.numerify(text='########'), 
                telefono=fake.numerify(text='9########'),
                fecha_nacimiento=fake.date_of_birth(minimum_age=20, maximum_age=70)
            )
            resident_user = CustomUser.objects.create_user(
                email=f'resident{i}@example.com',
                password='residentpassword',
                persona=res_persona,
                rol='RESIDENTE',
                complejo_asignado=random.choice(complejos)
            )
            resident_users.append(resident_user)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(resident_users)} Resident Users.'))

        # --- 4. Create Propiedades ---
        propiedades = []
        for complejo in complejos:
            for i in range(15):
                propiedad = Propiedad.objects.create(
                    complejo=complejo,
                    numero_identificador=f'Unidad {i+101}',
                    tipo=random.choice(['casa', 'departamento']),
                    area=f"{random.uniform(50.0, 200.0):.2f}",
                    numero_habitaciones=random.randint(1, 4),
                    numero_banos=random.randint(1, 3),
                    piso_nivel=str(random.randint(1, 10)),
                    valor_estimado=f"{random.uniform(100000, 500000):.2f}"
                )
                propiedades.append(propiedad)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(propiedades)} Propiedades.'))

        # --- 5. Assign Residents to Propiedades via PropiedadPersona ---
        for resident in resident_users:
            propiedad_asignada = random.choice([p for p in propiedades if p.complejo == resident.complejo_asignado])
            PropiedadPersona.objects.create(
                propiedad=propiedad_asignada,
                persona=resident,
                tipo_relacion=random.choice(['propietario', 'inquilino']),
                fecha_inicio=fake.date_between(start_date='-2y', end_date='today'),
                es_principal=True
            )
        self.stdout.write(self.style.SUCCESS('✓ Assigned Residents to Propiedades via PropiedadPersona.'))

        # --- 6. Create Avisos ---
        for _ in range(10):
            creador = random.choice(staff_users)
            Aviso.objects.create(
                complejo=creador.complejo_asignado,
                titulo=fake.sentence(nb_words=5),
                contenido=fake.paragraph(nb_sentences=4),
                autor=creador
            )
        self.stdout.write(self.style.SUCCESS('✓ Created 10 Avisos.'))

        # --- 7. Create Visitantes for Visitas & Preautorizaciones ---
        visitantes = []
        for _ in range(40):
            visitante = Visitante.objects.create(
                tipo_documento='DNI',
                numero_documento=fake.unique.numerify(text='########'),
                nombres=fake.first_name(),
                apellidos=fake.last_name()
            )
            visitantes.append(visitante)
        self.stdout.write(self.style.SUCCESS(f'✓ Created {len(visitantes)} Visitantes.'))

        residentes_con_propiedad = CustomUser.objects.filter(propiedades_asociadas__isnull=False).distinct()
        for _ in range(15):
            if not residentes_con_propiedad:
                continue
            residente_autoriza = random.choice(residentes_con_propiedad)
            prop_asociada = residente_autoriza.propiedades_asociadas.first().propiedad
            
            start_time = fake.date_time_between(start_date='+1d', end_date='+7d', tzinfo=datetime.timezone.utc)
            end_time = start_time + datetime.timedelta(days=1)

            PreAutorizacion.objects.create(
                residente=residente_autoriza,
                propiedad=prop_asociada,
                nombre_visitante=fake.name(),
                documento_visitante=fake.unique.numerify(text='########'),
                fecha_hora_esperada=start_time,
                vigencia_desde=start_time,
                vigencia_hasta=end_time
            )
        self.stdout.write(self.style.SUCCESS('✓ Created 15 PreAutorizaciones.'))

        # --- 8. Create Reservas ---
        for _ in range(30):
            residente_reserva = random.choice(resident_users)
            complejo_residente = residente_reserva.complejo_asignado
            if complejo_residente and complejo_residente.amenidades.exists():
                amenidad_a_reservar = random.choice(complejo_residente.amenidades.all())
                start_time = fake.date_time_between(start_date='+1d', end_date='+30d', tzinfo=datetime.timezone.utc)
                end_time = start_time + datetime.timedelta(hours=random.randint(1, 2))
                Reserva.objects.create(
                    residente=residente_reserva,
                    amenidad=amenidad_a_reservar,
                    fecha_inicio=start_time,
                    fecha_fin=end_time,
                    estado='confirmada'
                )
        self.stdout.write(self.style.SUCCESS('\nDatabase population complete!'))
        self.stdout.write(self.style.WARNING('Default passwords:'))
        self.stdout.write(self.style.WARNING('- Superuser: adminpassword'))
        self.stdout.write(self.style.WARNING('- Staff: staffpassword'))
        self.stdout.write(self.style.WARNING('- Resident: residentpassword'))
