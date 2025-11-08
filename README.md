# App Gestión Residencial

Este proyecto es un sistema integral para la gestión de complejos residenciales, condominios y propiedades. Permite a los administradores gestionar complejos, propiedades, residentes y amenidades, mientras que los residentes pueden reservar estas amenidades y gestionar sus visitas.

## Roles de Usuario y Permisos

El sistema define tres roles de usuario principales, cada uno con un conjunto específico de permisos y responsabilidades:

| Rol | Descripción | Permisos Clave |
| :--- | :--- | :--- |
| 👤 **Administrador** | Tiene control total sobre el sistema. Es responsable de la configuración inicial y la gestión de todos los datos maestros. | - CRUD completo de Complejos, Propiedades, y Amenidades.<br>- Gestión total de Contratos y Usuarios.<br>- Supervisión y gestión de todas las Reservas y Visitas. |
| 🏡 **Residente** | Es un usuario que habita en una propiedad. Su acceso está limitado a las funcionalidades relacionadas con su residencia. | - Realizar y gestionar sus propias reservas de amenidades.<br>- Crear y gestionar pre-autorizaciones para sus visitantes.<br>- Ver el historial de sus visitas y reservas. |
| 👮 **Guardia** | Personal de seguridad con acceso a la gestión de visitas. Su panel está enfocado en el control de acceso. | - Registrar la entrada y salida de visitantes.<br>- Consultar la lista de visitantes y pre-autorizaciones.<br>- Ver el dashboard de visitas en tiempo real. |

---

## Funcionalidades por Módulo

A continuación se detalla la funcionalidad de cada una de las aplicaciones que componen el sistema.

###  комплексы (Complejos)

Esta es la aplicación central del sistema y gestiona toda la lógica de negocio relacionada con las propiedades y sus activos.

#### Gestión de Complejos
- **Qué hace:** Permite a los administradores crear, listar, editar y filtrar los complejos residenciales.
- **Quién lo hace:** `Administrador`.
- **Dónde se muestra:**
    - `/complejos/`: Lista de complejos.
    - `/complejos/crear/`: Formulario para crear un nuevo complejo.
    - `/complejos/<id>/`: Detalle de un complejo.
- **Cómo lo hace:**
    - `models.Complejo`: Almacena la información de cada complejo.
    - `views.lista_complejos`, `views.crear_complejo`, `views.detalle_complejo`, `views.editar_complejo`: Controlan la lógica de negocio.
    - `templates/complejos/lista_complejos.html`, `crear_complejo.html`, `detalle_complejo.html`: Renderizan la interfaz.

#### Gestión de Propiedades
- **Qué hace:** Permite a los administradores crear propiedades (casas o departamentos) dentro de un complejo, ya sea de forma individual o masiva.
- **Quién lo hace:** `Administrador`.
- **Dónde se muestra:**
    - `/complejos/<id>/`: Las propiedades se listan en la vista de detalle del complejo.
    - `/complejos/<id>/crear_propiedad/`: Formulario para crear una propiedad.
    - `/propiedades/<id>/`: Detalle de una propiedad.
- **Cómo lo hace:**
    - `models.Propiedad`: Define la estructura de una propiedad.
    - `views.crear_propiedad`, `views.crear_propiedades_multiples`, `views.detalle_propiedad`: Vistas para la gestión.
    - `templates/complejos/crear_propiedad.html`, `detalle_propiedad.html`: Plantillas para la interfaz.

#### Gestión de Amenidades
- **Qué hace:** Permite a los administradores gestionar las amenidades de los complejos (piscinas, gimnasios, etc.), incluyendo la definición de reglas y horarios de funcionamiento.
- **Quién lo hace:** `Administrador`.
- **Dónde se muestra:**
    - `/amenidades/`: Panel de gestión de amenidades.
- **Cómo lo hace:**
    - `models.Amenidad`: Modelo que almacena la información de las amenidades.
    - `views.gestionar_amenidades_view`, `views.editar_amenidad_view`: Vistas para CRUD.
    - `templates/complejos/gestionar_amenidades.html`: Interfaz de gestión.

#### Gestión de Contratos
- **Qué hace:** Asigna una relación (propietario, inquilino) entre un usuario (residente) y una propiedad. Permite definir la duración del contrato y si el residente es el contacto principal.
- **Quién lo hace:** `Administrador`.
- **Dónde se muestra:**
    - `/contratos/`: Lista global de todos los contratos.
    - `/propiedades/<id>/asignar_contrato/`: Formulario para asignar un contrato a una propiedad.
- **Cómo lo hace:**
    - `models.PropiedadPersona`: Modelo "through" que conecta `Propiedad` y `CustomUser`.
    - `views.lista_contratos`, `views.asignar_contrato`, `views.editar_contrato`: Vistas para la gestión de contratos.
    - `templates/complejos/lista_contratos.html`, `asignar_contrato.html`: Plantillas.

#### Gestión de Reservas
- **Qué hace:** Permite a los residentes reservar amenidades y a los administradores gestionar estas reservas.
- **Quién lo hace:** `Residente` (crear y ver sus reservas), `Administrador` (gestión total).
- **Dónde se muestra:**
    - `/reservas/crear/`: (Residente) Panel para iniciar una reserva.
    - `/reservas/mis_reservas/`: (Residente) Historial de reservas personales.
    - `/reservas/disponibilidad/<id>/`: Calendario de disponibilidad de una amenidad.
    - `/admin/reservas/`: (Admin) Panel de gestión de todas las reservas.
- **Cómo lo hace:**
    - `models.Reserva`: Almacena los datos de cada reserva.
    - `views.crear_reserva_view`, `views.mis_reservas_view`, `views.ver_disponibilidad_view`: Vistas para residentes.
    - `views.admin_reservas_view`, `views.approve_reserva`, `views.reject_reserva`: Vistas para administradores.
    - `templates/complejos/crear_reserva.html`, `ver_disponibilidad.html`: Plantillas de reserva.

---

### users (Usuarios)

Esta aplicación gestiona todo lo relacionado con los usuarios, sus perfiles y la autenticación.

#### Gestión de Usuarios
- **Qué hace:** Permite a los administradores crear, listar, editar y activar/desactivar usuarios del sistema.
- **Quién lo hace:** `Administrador`.
- **Dónde se muestra:**
    - `/usuarios/`: Lista de todos los usuarios.
    - `/usuarios/crear/`: Formulario de creación de usuario.
    - `/usuarios/<id>/`: Detalle de un usuario.
- **Cómo lo hace:**
    - `models.CustomUser`, `models.Persona`: Modelos para la información del usuario y su perfil personal.
    - `views.lista_usuarios_view`, `views.crear_usuario_view`, `views.detalle_usuario_view`, `views.editar_usuario_view`: Vistas para la gestión de usuarios.
    - `templates/users/lista_usuarios.html`, `crear_usuario.html`: Plantillas.

#### Autenticación y Dashboard
- **Qué hace:** Controla el inicio de sesión y muestra un panel de control (dashboard) personalizado según el rol del usuario.
- **Quién lo hace:** Todos los usuarios.
- **Dónde se muestra:**
    - `/login/`: Página de inicio de sesión.
    - `/`: Dashboard principal.
- **Cómo lo hace:**
    - `django.contrib.auth.views.LoginView`: Vista de Django para el login.
    - `views.dashboard`: Vista que redirige o renderiza el dashboard según el rol.
    - `templates/users/login.html`, `dashboard.html`: Plantillas.

---

### visitas (Visitas)

Esta aplicación se encarga del control de acceso de visitantes a los complejos.

#### Gestión de Visitantes
- **Qué hace:** Permite registrar y gestionar una base de datos de visitantes, incluyendo la posibilidad de marcarlos como frecuentes o bloquearlos.
- **Quién lo hace:** `Administrador`, `Guardia`.
- **Dónde se muestra:**
    - `/visitas/visitantes/`: Lista de visitantes.
    - `/visitas/visitantes/crear/`: Formulario para registrar un nuevo visitante.
- **Cómo lo hace:**
    - `models.Visitante`: Modelo para almacenar los datos de los visitantes.
    - `views.lista_visitantes_view`, `views.crear_visitante_view`: Vistas para la gestión.
    - `templates/visitas/lista_visitantes.html`: Plantilla.

#### Registro de Visitas
- **Qué hace:** Registra la entrada y salida de visitantes a una propiedad, asociando la visita a un residente que autoriza.
- **Quién lo hace:** `Guardia`.
- **Dónde se muestra:**
    - `/visitas/`: Dashboard de visitas para el guardia.
    - `/visitas/visitas/`: Historial de todas las visitas.
    - `/visitas/visitas/crear/`: Formulario para registrar una nueva visita.
- **Cómo lo hace:**
    - `models.Visita`: Modelo que registra cada evento de visita.
    - `views.lista_visitas_view`, `views.crear_visita_view`: Vistas para el registro.
    - `templates/visitas/lista_visitas.html`: Plantilla.

#### Pre-Autorizaciones
- **Qué hace:** Permite a los residentes crear autorizaciones de acceso para sus visitantes con antelación, especificando un rango de fechas y horas.
- **Quién lo hace:** `Residente`.
- **Dónde se muestra:**
    - `/visitas/preautorizaciones/`: (Residente) Lista de sus pre-autorizaciones.
    - `/visitas/preautorizaciones/crear/`: (Residente) Formulario para crear una nueva pre-autorización.
- **Cómo lo hace:**
    - `models.PreAutorizacion`: Modelo para las autorizaciones previas.
    - `views.lista_preautorizaciones_view`, `views.crear_preautorizacion_view`: Vistas para la gestión.
    - `templates/visitas/lista_preautorizaciones.html`: Plantilla.

---

## Modelos de la Base de Datos

A continuación se describe la estructura de los modelos más importantes del sistema.

| Modelo | App | Descripción | Relaciones Clave |
| :--- | :--- | :--- | :--- |
| `Complejo` | `complejos` | Representa un complejo residencial o condominio. | `Amenidad` (M2M), `CustomUser` (1-M) |
| `Propiedad` | `complejos` | Una casa o departamento dentro de un `Complejo`. | `Complejo` (M-1), `CustomUser` (M2M via `PropiedadPersona`) |
| `Amenidad` | `complejos` | Un área común que puede ser reservada (piscina, etc.). | `Complejo` (M2M) |
| `PropiedadPersona` | `complejos` | Tabla intermedia que define la relación entre un `CustomUser` y una `Propiedad`. | `Propiedad` (M-1), `CustomUser` (M-1) |
| `Reserva` | `complejos` | Una reserva de una `Amenidad` por un `CustomUser`. | `Amenidad` (M-1), `CustomUser` (M-1) |
| `Persona` | `users` | Almacena los datos personales de un individuo. | `CustomUser` (1-1) |
| `CustomUser` | `users` | El modelo de usuario del sistema. | `Persona` (1-1), `Complejo` (M-1) |
| `Visitante` | `visitas` | Una persona que visita el complejo. | - |
| `Visita` | `visitas` | El registro de una visita de un `Visitante` a una `Propiedad`. | `Visitante` (M-1), `Propiedad` (M-1), `CustomUser` (M-1) |
| `PreAutorizacion` | `visitas` | Una autorización de visita creada por un `Residente`. | `CustomUser` (M-1), `Propiedad` (M-1) |

---

## Stack Tecnológico
- **Backend:** Python, Django
- **Frontend:** HTML, CSS, JavaScript
- **Base de Datos:** SQLite (por defecto en la configuración de Django)

## Instalación y Configuración Local

Sigue estos pasos para poner en marcha el proyecto en un entorno de desarrollo:

1.  **Clonar el Repositorio:**
    ```bash
    git clone git@github.com:RichardAgapito/App-Gesti-n-Residencias.git
    cd App-Gesti-n-Residencias
    ```

2.  **Crear y Activar el Entorno Virtual:**
    ```bash
    # Crear el entorno virtual
    python -m venv venv

    # Activar en Linux/macOS
    source venv/bin/activate

    # Activar en Windows
    .\venv\Scripts\activate
    ```

3.  **Instalar Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Ejecutar Migraciones:**
    Para crear el esquema de la base de datos.
    ```bash
    python manage.py migrate
    ```

5.  **Crear un Superusuario:**
    Necesitarás un usuario administrador para acceder a los paneles de gestión.
    ```bash
    python manage.py createsuperuser
    ```
    Sigue las instrucciones en pantalla para crear tu usuario.

6.  **Ejecutar el Servidor de Desarrollo:**
    ```bash
    python manage.py runserver
    ```
    El proyecto estará disponible en `http://127.0.0.1:8000/`.

## Estructura del Proyecto

El proyecto está organizado en tres aplicaciones principales de Django:

-   `complejos`: Contiene toda la lógica de negocio para complejos, propiedades, amenidades y el sistema de reservas.
-   `users`: Gestiona los perfiles de usuario, la autenticación y los roles (Administrador, Residente).
-   `visitas`: Maneja la lógica para el registro de visitantes, pre-autorizaciones y control de acceso.

## Análisis y Mejoras

Durante la revisión del proyecto, se identificaron y corrigieron varios aspectos clave. También se proponen mejoras a futuro.

### Bugs Corregidos
1.  **Iconos Faltantes en Calendario:** Los iconos de navegación (mes anterior/siguiente) en los calendarios no se mostraban debido a un conflicto de estilos CSS que afectaba el `font-weight` de Font Awesome. Se solucionó con una regla CSS específica.
2.  **Lógica de Bloqueo en la Interfaz:**
    -   **Admin:** El panel de administrador no mostraba los horarios bloqueados ni permitía desbloquearlos. Se modificó la plantilla para listar los bloqueos y añadir un botón de "Desbloquear".
    -   **Residente:** Una amenidad con un bloqueo futuro aparecía como completamente bloqueada en el presente. Se corrigió la lógica en la plantilla de selección de amenidades para permitir siempre el acceso al calendario de disponibilidad.
3.  **Feedback Visual en Calendario:** Los días completamente ocupados no se diferenciaban visualmente de los días con disponibilidad parcial. Se implementó una función en JavaScript (`isDayFullyBooked`) para analizar la disponibilidad de un día y añadir una clase CSS que lo deshabilita y tacha si no quedan horarios libres.
4.  **Desfase Horario (Timezone Bug):** La lógica de bloqueo y reserva tenía un desfase de horas. Esto se debía a que las fechas del servidor (en UTC) eran interpretadas por JavaScript en la zona horaria local del navegador. Se solucionó estandarizando el formato de fecha que Django entrega a JavaScript para que sea interpretado consistentemente como hora local.
5.  **Validación de Horarios en Backend:** El sistema permitía crear reservas fuera del horario de funcionamiento de la amenidad si la petición se enviaba directamente al backend. Se añadió lógica de validación en los métodos `clean` de los formularios (`ReservaForm`, `BloquearHorarioForm`, `AdminReservaForm`) para rechazar cualquier reserva que no respete la `hora_inicio` y `hora_fin` de la amenidad.
6.  **Mensajes de Error Ausentes:** Las validaciones del backend fallaban de forma silenciosa. Se añadieron bloques en las plantillas para renderizar y mostrar al usuario los mensajes de error devueltos por el formulario.

### Posibles Mejoras a Futuro
-   **Refactorizar CSS:** Actualmente, muchas plantillas contienen grandes bloques `<style>`. Sería beneficioso mover estos estilos a archivos `.css` externos para mejorar la mantenibilidad y el cacheo del navegador.
-   **Roles y Permisos:** El sistema de permisos se basa en la función `es_admin`. Se podría refactorizar para usar el sistema de grupos y permisos nativo de Django, que es más robusto y escalable.
-   **Desarrollo de API:** Considerar el uso de **Django Rest Framework** para construir una API RESTful. Esto permitiría en el futuro crear un frontend desacoplado (ej. una Single Page Application con React/Vue) o una aplicación móvil.
-   **Cobertura de Pruebas:** El proyecto tiene archivos `tests.py` pero la cobertura podría expandirse para incluir pruebas unitarias y de integración para la lógica de reservas, bloqueos y validaciones de horarios.
-   **Generación de QR para Visitas:** La app `visitas` es ideal para implementar una funcionalidad de generación de códigos QR para las pre-autorizaciones, que podrían ser enviados a los visitantes para un acceso rápido y seguro.
-   **Internacionalización (i18n):** Preparar el proyecto para múltiples idiomas, aunque actualmente está en español.