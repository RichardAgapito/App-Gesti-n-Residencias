# App Gestión Residencial

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.x-0C4B33?logo=django&logoColor=white)
![Estado](https://img.shields.io/badge/Status-Proyecto%20colaborativo-ffb347)

> Guía técnica para la exposición: este README explica qué hace cada componente del repositorio para que cualquier integrante pueda contar cómo funciona el sistema sin tener que bucear en el código.

## 📚 Tabla de Contenidos
1. [Panorama rápido del sistema](#-panorama-rápido-del-sistema)
2. [Mapa del repositorio](#-mapa-del-repositorio)
3. [Arquitectura por aplicación](#-arquitectura-por-aplicación)
4. [Flujos de negocio y puntos de código](#-flujos-de-negocio-y-puntos-de-código)
5. [Modelos y relaciones](#-modelos-y-relaciones)
6. [Formularios y validaciones server-side](#-formularios-y-validaciones-server-side)
7. [Frontend, plantillas y JS](#-frontend-plantillas-y-js)
8. [Puesta en marcha](#-puesta-en-marcha)
9. [Datos auxiliares y comandos útiles](#-datos-auxiliares-y-comandos-útiles)
10. [Checklist para la demo](#-checklist-para-la-demo)
11. [Contribuciones](#-contribuciones)

---

## 🚀 Panorama rápido del sistema
- **Caso de uso**: administración integral de complejos residenciales (inventario de propiedades, contratos, amenidades y reservas) con control de accesos y visitas.
- **Roles soportados**:
  - 👤 **Administrador**: alta/mantenimiento de complejos, propiedades, amenidades, contratos y usuarios; aprueba o bloquea reservas.
  - 🏡 **Residente**: consulta amenidades del complejo, agenda reservas y crea pre-autorizaciones de visitas.
  - 👮 **Guardia**: controla visitas presenciales, consulta autorizaciones y mantiene un dashboard operativo.
- **Apps Django**:
  - `complejos/`: inventario, contratos y reservas (núcleo del dominio).
  - `users/`: autenticación, dashboards y CRUD de usuarios.
  - `visitas/`: visitantes, visitas y pre-autorizaciones (flujo de seguridad).
- **Entradas principales**:
  - `config/urls.py` enruta el dashboard público (`users`) y los submódulos de admin (`complejos`) y seguridad (`visitas`).
  - `templates/base.html` y `templates/base_dashboard.html` definen los layouts comunes.

---

## 🗂️ Mapa del repositorio

| Ruta | Qué contiene | Archivos clave |
| :--- | :--- | :--- |
| `manage.py` | Punto de entrada para comandos Django. | `python manage.py runserver`, `migrate`, etc. |
| `config/` | Configuración global del proyecto. | `settings.py` (apps instaladas, base de datos, auth), `urls.py` (routing raíz). |
| `complejos/` | Dominio principal: modelos de inventario, forms, vistas, templates y management commands. | `models.py`, `forms.py`, `views.py`, `urls.py`, `management/commands/*.py`. |
| `users/` | Modelo de usuario, formularios de alta/edición, dashboard y panel de administración interno. | `models.py`, `forms.py`, `views.py`, `urls.py`. |
| `visitas/` | Todo el flujo de visitantes/visitas/pre-autorizaciones + endpoints auxiliares. | `models.py`, `forms.py`, `views.py`, `urls.py`. |
| `templates/` | Layouts compartidos (base, dashboard). | `base.html`, `base_dashboard.html`. |
| `static/` | Recursos estáticos globales (CSS por rol). | `css/resident_dashboard.css`, otros estilos auxiliares. |
| `requirements.txt` | Dependencias (Django, Pillow para imágenes de visitantes, etc.). | Usar con `pip install -r requirements.txt`. |
| `db.sqlite3` | Base de datos local por defecto (puede regenerarse vía migraciones). | No se versiona en producción. |

---

## 🏗️ Arquitectura por aplicación

### `complejos/` — Inventario, contratos y reservas
- **Modelos (`complejos/models.py`)**
  - `Amenidad`: define reglas, capacidad y horario (campos `hora_inicio`/`hora_fin` controlan reservas).
  - `Complejo`: ficha del condominio (datos de contacto, tipo, amenidades asociadas).
  - `Propiedad`: unidades; guarda número identificador autogenerado, dimensiones, estado de ocupación y relación con residentes vía `PropiedadPersona`.
  - `PropiedadPersona`: contrato entre un `CustomUser` y una propiedad, con tipo (propietario/inquilino/co-*), fechas y flag `es_principal`.
  - `Reserva`: bloque de tiempo sobre una amenidad; admite estados `pendiente/confirmada/cancelada/completada/bloqueada`.
- **Formularios (`complejos/forms.py`)**
  - Validan teléfono del complejo, fechas de contrato, reglas de co-propietarios, y conflictos de horarios en reservas.
  - `ReservaForm`, `AdminReservaForm` y `BloquearHorarioForm` aseguran que las solicitudes respeten los horarios de la amenidad e impiden traslapes.
- **Vistas (`complejos/views.py`)**
  - CRUD de complejos/propiedades, alta masiva, filtros por estado.
  - Gestión de contratos (alta individual y global) con transacciones y lógica para promover co-propietarios.
  - Módulo completo de reservas para residentes (calendario + disponibilidad) y panel administrativo (aprobar/cancelar/bloquear).
  - Gestión de amenidades con prefetch de bloqueos (`models.Prefetch`), bloqueo/desbloqueo de franjas y API auxiliar para residentes (`get_residentes_json`).
- **Management commands (`complejos/management/commands`)**
  - `actualizar_reservas.py`: marca como `completada` toda reserva confirmada cuyo `fecha_fin` ya pasó.
  - `populate_amenities.py`: script para rellenar descripciones/capacidades; requiere que el modelo tenga las columnas referenciadas (útil como ejemplo de migración de datos).
- **Templates**: ubicados en `complejos/templates/complejos/`, e incluyen las pantallas de `gestionar_amenidades.html`, `crear_reserva.html`, `ver_disponibilidad.html`, etc., con bloques `<style>` específicos y lógica JS para calendarios.

### `users/` — Autenticación y panel administrativo
- **Modelos (`users/models.py`)**
  - `Persona`: datos personales desacoplados (documento, nombres, teléfono, cumpleaños).
  - `CustomUser`: `AbstractBaseUser` con campo `rol` (`ADMIN`, `RESIDENTE`, `GUARDIA`) y FK opcional a `Complejo` (para guardias).
- **Formularios (`users/forms.py`)**
  - `CustomUserCreationForm`: crea usuario + `Persona`, valida edad mínima, unicidad de documentos y asignación exclusiva de guardias.
  - `EditarUsuarioForm`: permite al admin editar datos personales y activar/desactivar usuarios.
- **Vistas/URLs (`users/views.py`, `users/urls.py`)**
  - `dashboard`: enruta según rol (admin → métricas básicas, guardia → `visitas/dashboard`, residente → dashboard simple).
  - CRUD completo para usuarios, con filtros por rol/estado y toggles de activación.
  - Usa las vistas de auth estándar (`LoginView`, `LogoutView`) con plantillas en `users/templates/users/`.

### `visitas/` — Seguridad y control de acceso
- **Modelos (`visitas/models.py`)**
  - `Visitante`: identidad de visitantes, bandera `es_frecuente` y foto opcional (`ImageField`).
  - `Visita`: registro de ingresos; guarda motivo, placas, acompañantes, quién autoriza y quién registra (guardia).
  - `PreAutorizacion`: autorizaciones adelantadas con vigencia y estado operacional (`pendiente`, `usado`, etc.).
- **Formularios (`visitas/forms.py`)**
  - Normalizan documentos y teléfonos, filtran propiedades para guardias según `complejo_asignado` y dejan `residente_autoriza` opcional.
- **Vistas/URLs (`visitas/views.py`, `visitas/urls.py`)**
  - Dashboard operativo (conteo de visitantes dentro y autorizaciones pendientes).
  - CRUD para visitantes, visitas y pre-autorizaciones, con filtros (`models.Q`) por texto, estado y motivo.
  - Endpoint `get_residentes_por_propiedad` devuelve residentes activos (se usa vía AJAX en formularios de visitas).

### `templates/` y `static/`
- `templates/base.html`: layout para residentes/guardias (navbar, bloques de contenido).
- `templates/base_dashboard.html`: layout administrativo, incluye sidebar y enlaces a listas de complejos/usuarios/reservas.
- `static/css/resident_dashboard.css`: comportamientos visuales compartidos (paleta azul/verde, cards, etc.).
- Los módulos agregan estilos embebidos cuando necesitan layouts específicos (ej. calendario interactivo de `ver_disponibilidad.html`).

---

## 🔁 Flujos de negocio y puntos de código

| Flujo | Qué hace | Código relevante |
| :--- | :--- | :--- |
| Alta de complejo y propiedades | Admin crea complejo, luego agrega propiedades individuales o en lote (con prefijo `P-` o `D-`). | `complejos/views.lista_complejos`, `crear_complejo`, `crear_propiedad`, `crear_propiedades_multiples`; templates `lista_complejos.html`, `crear_propiedad.html`. |
| Asignación de contratos | Define relación usuario-propiedad (propietario, inquilino, co-*), controla fechas mínimas y persona principal. | `PropiedadPersona` (modelo), `PropiedadPersonaForm` y `GlobalContratoForm` (validaciones de fechas y duplicados), vistas `asignar_contrato`, `crear_contrato_global`, `lista_contratos`. |
| Gestión de amenidades | Admin crea/edita amenidades, bloquea franjas y ve bloqueos vigentes. | `gestionar_amenidades_view`, `bloquear_horario_view`, `unblock_horario_view`; plantillas `gestionar_amenidades.html`, `bloquear_horario.html`. |
| Reservas del residente | Residente navega a `crear_reserva`, ve amenidades del complejo vinculado, consulta calendario (`ver_disponibilidad_view`) y envía formulario. | `PropiedadPersona` → obtiene complejo; `ReservaForm` valida solapamientos; `ver_disponibilidad.html` contiene calendario dinámico y slots. |
| Panel de reservas admin | Admin ve todas las reservas, filtra por complejo/amenidad/estado, crea o edita reservas en nombre del residente, y aprueba/cancela. | `admin_reservas_view`, `admin_crear_reserva`, `admin_editar_reserva`, `approve_reserva`, `reject_reserva`, `cancelar_reserva_view`. |
| Control de visitas | Guardia registra visitantes, asigna residentes autorizadores y marca salidas; residentes pueden crear pre-autorizaciones que aparecen al guardia. | Modelos `Visitante`, `Visita`, `PreAutorizacion`; vistas `lista_visitas_view`, `crear_visita_view`, `lista_preautorizaciones_view`; formularios en `visitas/forms.py`. |
| Actualización automática | Cron/manual: `python manage.py actualizar_reservas` pasa reservas confirmadas a `completada` cuando termina la franja. | `complejos/management/commands/actualizar_reservas.py`. |

---

## 🗃️ Modelos y relaciones

| Modelo | App | Relación clave | Uso principal |
| :--- | :--- | :--- | :--- |
| `Complejo` | `complejos` | M2M con `Amenidad`, 1-M con `Propiedad`. | Agrupa propiedades, define tipo y estado. |
| `Propiedad` | `complejos` | FK a `Complejo`, M2M a `CustomUser` vía `PropiedadPersona`. | Unidades habitacionales con metadatos de superficie y ocupación. |
| `PropiedadPersona` | `complejos` | FK a `Propiedad` y `CustomUser`. | Contratos (propietario/inquilino) con rango de fechas y rol principal. |
| `Amenidad` | `complejos` | M2M con `Complejo`, relacionada con `Reserva`. | Reglas de uso, capacidad y horarios. |
| `Reserva` | `complejos` | FK a `Amenidad` y `CustomUser`. | Bloques confirmados o bloqueados en el calendario. |
| `Persona` | `users` | 1-1 con `CustomUser`. | Datos personales normalizados. |
| `CustomUser` | `users` | FK opcional a `Complejo` (guardia). | Usuario autenticado con rol. |
| `Visitante` | `visitas` | - | Identidad de visitantes, estado y fotografía. |
| `Visita` | `visitas` | FK a `Visitante`, `Propiedad` y `CustomUser` (residentes y guardias). | Control de accesos en tiempo real. |
| `PreAutorizacion` | `visitas` | FK a `CustomUser` y `Propiedad`. | Códigos de autorización anticipada. |

---

## ✅ Formularios y validaciones server-side
- **Contactos y usuarios**:
  - `CustomUserCreationForm` exige documentos únicos (`Persona.numero_documento`), teléfonos con prefijo `9` y mayor de 18 años.
  - `EditarUsuarioForm` sincroniza `Persona` e `is_active`.
- **Contratos**:
  - `PropiedadPersonaForm` y `GlobalContratoForm` verifican roles incompatibles (nadie puede ser propietario e inquilino activo a la vez), fechas mínimas de 30 días para inquilinos y unicidad del principal.
- **Reservas**:
  - `ReservaForm`, `AdminReservaForm`, `BloquearHorarioForm` impiden reservas en el pasado, garantizan que `fecha_fin > fecha_inicio` y que el horario quede dentro de `Amenidad.hora_inicio/hora_fin`.
- **Visitas**:
  - `VisitanteForm` valida patrón de documentos (DNI/Pasaporte 8 dígitos, Carnet 9), teléfonos numéricos y nombres solo con letras.
  - `VisitaForm` filtra propiedades según el complejo del guardia para evitar incoherencias.

---

## 🎨 Frontend, plantillas y JS
- **Layouts**:
  - `base_dashboard.html` arma el sidebar del administrador con links hacia complejos, contratos, reservas y usuarios.
  - `base.html` sirve a residentes y guardias; incluye navegación superior y bloque para inyectar estilos específicos por página.
- **Calcular disponibilidad (residente)**:
  - `ver_disponibilidad.html` renderiza calendario y slots usando datos que `ver_disponibilidad_view` envía (`reservas` confirmadas/bloqueadas).
  - Script inline calcula días completos (`fully-booked`) y controla selección de rangos antes de enviar el form.
- **Gestión visual de amenidades**:
  - `gestionar_amenidades.html` muestra cards por amenidad con bloqueos activos y botones de edición, reutilizando `resident_dashboard.css`.
- **Panel de visitas**:
  - Plantillas en `visitas/templates/visitas/` se apoyan en tablas + filtros; AJAX para `get_residentes_por_propiedad` se realiza desde los formularios mediante fetch.

---

## ⚙️ Puesta en marcha
```bash
# 1. Clonar
git clone git@github.com:RichardAgapito/App-Gesti-n-Residencias.git
cd App-Gesti-n-Residencias

# 2. Entorno virtual
python -m venv venv
source venv/bin/activate    # Windows: .\venv\Scripts\activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Migraciones (SQLite por defecto)
python manage.py migrate

# 5. Crear superusuario
python manage.py createsuperuser

# 6. Servidor de desarrollo
python manage.py runserver
```
Aplicación disponible en `http://127.0.0.1:8000/`. El login redirige al dashboard según rol.

---

## 📦 Datos auxiliares y comandos útiles
- **Actualizar estados de reservas**  
  `python manage.py actualizar_reservas`
- **Popular amenidades existentes** (dejar campos descriptivos consistentes; requiere ajustar el modelo si faltan columnas)  
  `python manage.py populate_amenities`
- **Carga manual**  
  - Crear un `Complejo` desde `/admin_dashboard/complejos/crear/`.
  - Asociar amenidades y generar propiedades (opción individual o múltiple).
  - Crear usuarios residentes y vincularlos mediante `PropiedadPersona`.
  - Probar reservas con una cuenta residente y verificar la vista admin.

---

## 🎤 Checklist para la demo
1. **Inicio de sesión** con cada rol y mostrar redirecciones automáticas (`users/views.dashboard`).
2. **Inventario**: listar complejos, mostrar filtros y abrir detalle para ver propiedades (`detalle_complejo.html`).
3. **Contratos**: enseñar cómo se asigna un propietario/inquilino y cómo el estado de la propiedad cambia a `ocupado`.
4. **Amenidades y reservas**:
   - Crear/editar amenidad.
   - Bloquear horario desde `gestionar_amenidades`.
   - Cambiar al rol residente, entrar a `crear_reserva`, elegir amenidad y mostrar calendario (cómo se ven bloqueos y reservas confirmadas).
   - Aprobar/cancelar desde el panel admin para mostrar estados.
5. **Visitas**:
   - Guardias ven el dashboard de `visitas`, registran visita y consumen pre-autorización.
   - Mostrar endpoint de residentes por propiedad (AJAX).
6. **Comandos**: mencionar que `actualizar_reservas` corre como tarea programada para mantener la data limpia.

Preparar capturas o flujos cortos para cada punto y dividir la explicación por persona (inventario, reservas, visitas, usuarios).

---

## 🤝 Contribuciones
1. Crear un branch descriptivo (`feature/reservas-multi-complejo`).
2. Añadir o actualizar pruebas si se tocan reglas de negocio (formularios o management commands).
3. Ejecutar chequeos básicos (`python manage.py test` si hay suites) antes del PR.
4. Enviar el PR detallando:
   - Qué módulo tocaste.
   - Cómo probarlo (URL, rol, datos).
   - Capturas si el cambio es visual.

Issues con contexto (pasos para reproducir y rol involucrado) ayudan a distribuir el trabajo en el equipo.
