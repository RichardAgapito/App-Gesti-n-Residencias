# App Gestión Residencial

Este proyecto es un sistema integral para la gestión de complejos residenciales, condominios y propiedades. Permite a los administradores gestionar complejos, propiedades, residentes y amenidades, mientras que los residentes pueden reservar estas amenidades y gestionar sus visitas.

## Características Principales

El sistema está dividido principalmente en dos roles con diferentes capacidades:

### Panel de Administrador
- **Gestión de Complejos:** Crear, editar y listar complejos residenciales o condominios.
- **Gestión de Propiedades:** Crear y editar propiedades (casas, apartamentos) dentro de un complejo.
- **Gestión de Contratos:** Asignar residentes (propietarios, inquilinos) a las propiedades, definiendo la relación y duración del contrato.
- **Gestión de Amenidades:**
    - Crear, editar y eliminar amenidades (ej. parques, piscinas, salones de eventos).
    - Definir horarios de funcionamiento (hora de inicio y fin) que son respetados por el sistema de reservas.
- **Bloqueo de Horarios:** Utilizar una interfaz de calendario visual para bloquear rangos de fechas/horas en las amenidades, haciéndolas no disponibles para reservas.
- **Gestión de Reservas:** Ver un listado completo de todas las reservas, con la capacidad de aprobar, rechazar o cancelar.
- **Gestión de Usuarios:** Creación y administración de usuarios del sistema (Administradores, Residentes).

### Panel de Residente
- **Dashboard Principal:** Acceso rápido a las funciones principales.
- **Sistema de Reservas:**
    - Ver una lista de las amenidades disponibles en su complejo.
    - Acceder a un calendario de disponibilidad visual para cada amenidad.
    - Seleccionar y reservar franjas horarias de una hora.
    - Los horarios de funcionamiento de la amenidad se reflejan dinámicamente en el calendario.
- **Mis Reservas:** Ver un historial de todas las reservas realizadas por el usuario.
- **Gestión de Visitas (App `visitas`):**
    - Registrar visitantes frecuentes.
    - Crear pre-autorizaciones de acceso para visitantes.
    - Ver un historial de visitas.

## Stack Tecnológico
- **Backend:** Python, Django
- **Frontend:** HTML, CSS, JavaScript
- **Base de Datos:** SQLite (por defecto en la configuración de Django)

## Instalación y Configuración Local

Sigue estos pasos para poner en marcha el proyecto en un entorno de desarrollo:

1.  **Clonar el Repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
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
