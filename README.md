# App Gestión Residencial

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.x-0C4B33?logo=django&logoColor=white)
![SQLite](https://img.shields.io/badge/DB-SQLite-044a64?logo=sqlite&logoColor=white)
![Estado](https://img.shields.io/badge/Estado-En%20desarrollo-ffb347)

> Plataforma integral para la administración de complejos, reservas de amenidades y control de visitas en condominios.

## 🧭 Tabla de Contenidos
- [Características Clave](#-características-clave)
- [Roles y Permisos](#-roles-y-permisos)
- [Módulos Principales](#-módulos-principales)
- [Modelos de Datos](#-modelos-de-datos)
- [Stack Tecnológico](#-stack-tecnológico)
- [Puesta en Marcha](#-puesta-en-marcha)
- [Estructura de Apps](#-estructura-de-apps)
- [Calidad y Roadmap](#-calidad-y-roadmap)

## 🚀 Características Clave
- Paneles especializados para administradores, residentes y guardias.
- Reservas de amenidades con bloqueo de horarios, reglas y validaciones en backend.
- Registro de visitas y pre-autorizaciones con trazabilidad completa.
- Gestión masiva de propiedades, contratos, amenidades y usuarios desde un mismo lugar.
- UI pensada para calendarios de disponibilidad con feedback visual y validaciones en tiempo real.

## 🛡️ Roles y Permisos
| Rol | Enfoque | Capacidades clave |
| :--- | :--- | :--- |
| 👤 **Administrador** | Configura y opera todo el ecosistema. | CRUD completo de complejos, propiedades y amenidades · Gestión total de contratos, usuarios, reservas y visitas.
| 🏡 **Residente** | Consume servicios del complejo. | Realiza y administra sus reservas · Genera pre-autorizaciones · Consulta historial personal.
| 👮 **Guardia** | Control de acceso y monitoreo. | Registra entradas/salidas · Consulta visitantes y autorizaciones · Opera panel en tiempo real.

## 🧩 Módulos Principales
Cada sección resume el flujo, las pantallas y los artefactos relevantes.

<details>
<summary><strong>🏢 Complejos</strong> — núcleo del sistema</summary>

- **Qué hace:** CRUD de complejos residenciales y filtros por atributos clave.
- **Quién:** Administrador.
- **Dónde:** `/complejos/`, `/complejos/crear/`, `/complejos/<id>/`.
- **Cómo:** `models.Complejo`, vistas `lista/crear/detalle/editar`, plantillas en `templates/complejos/*`.
</details>

<details>
<summary><strong>🏘️ Propiedades</strong> — unidades dentro de cada complejo</summary>

- **Qué hace:** Alta individual o masiva de propiedades y gestión detallada.
- **Quién:** Administrador.
- **Dónde:** `/complejos/<id>/`, `/complejos/<id>/crear_propiedad/`, `/propiedades/<id>/`.
- **Cómo:** `models.Propiedad`, vistas `crear_propiedad`, `crear_propiedades_multiples`, `detalle_propiedad`.
</details>

<details>
<summary><strong>🏊 Amenidades</strong> — áreas comunes reservables</summary>

- **Qué hace:** Define reglas, horarios de operación y capacidad por amenidad.
- **Quién:** Administrador.
- **Dónde:** `/amenidades/` y flujo de edición.
- **Cómo:** `models.Amenidad`, vistas `gestionar_amenidades_view`, `editar_amenidad_view`, plantilla `gestionar_amenidades.html`.
</details>

<details>
<summary><strong>📄 Contratos</strong> — vinculación residente/propiedad</summary>

- **Qué hace:** Asigna roles (propietario, inquilino), fechas y contacto principal.
- **Quién:** Administrador.
- **Dónde:** `/contratos/`, `/propiedades/<id>/asignar_contrato/`.
- **Cómo:** `models.PropiedadPersona`, vistas `lista_contratos`, `asignar_contrato`, `editar_contrato`.
</details>

<details>
<summary><strong>📅 Reservas</strong> — experiencia de amenidades</summary>

- **Qué hace:** Gestiona calendarios, bloqueos y reservas con validación de horarios.
- **Quién:** Residentes (crean/consultan) y administradores (moderan).
- **Dónde:** `/reservas/crear/`, `/reservas/mis_reservas/` y panel administrativo.
- **Cómo:** Formularios `ReservaForm`, `BloquearHorarioForm`, `AdminReservaForm`; lógica JS para estados del calendario.
</details>

<details>
<summary><strong>🙋 Usuarios</strong> — perfiles y autenticación</summary>

- **Qué hace:** Maneja perfiles, roles y datos personales.
- **Quién:** Administrador.
- **Dónde:** Panel de usuarios de Django + vistas personalizadas.
- **Cómo:** `users.models.Persona`, `CustomUser` y señales asociadas.
</details>

<details>
<summary><strong>🛂 Visitas & Pre-autorizaciones</strong> — seguridad y accesos</summary>

- **Qué hace:** Registro de visitantes, check-in/out, dashboard para guardias y autorizaciones previas de residentes.
- **Quién:** Guardias (operación diaria) y residentes (pre-autorizan).
- **Dónde:** `/visitas/`, `/visitas/visitas/`, `/visitas/visitas/crear/`, `/visitas/preautorizaciones/`.
- **Cómo:** Modelos `Visitante`, `Visita`, `PreAutorizacion`; vistas `lista_visitas_view`, `crear_visita_view`, `lista_preautorizaciones_view`, `crear_preautorizacion_view`.
</details>

## 🗃️ Modelos de Datos
| Modelo | App | Descripción | Relaciones clave |
| :--- | :--- | :--- | :--- |
| `Complejo` | `complejos` | Conjunto residencial o condominio. | `Amenidad` (M2M), `CustomUser` (1-M).
| `Propiedad` | `complejos` | Unidad habitacional dentro de un complejo. | `Complejo` (M-1), `CustomUser` (M2M via `PropiedadPersona`).
| `Amenidad` | `complejos` | Área común reservable. | `Complejo` (M2M).
| `PropiedadPersona` | `complejos` | Relación usuario-propiedad y tipo de contrato. | `Propiedad` (M-1), `CustomUser` (M-1).
| `Reserva` | `complejos` | Reserva de amenidad. | `Amenidad` (M-1), `CustomUser` (M-1).
| `Persona` | `users` | Datos personales extendidos. | `CustomUser` (1-1).
| `CustomUser` | `users` | Usuario autenticado del sistema. | `Persona` (1-1), `Complejo` (M-1).
| `Visitante` | `visitas` | Invitado registrado. | - |
| `Visita` | `visitas` | Evento de acceso a la propiedad. | `Visitante` (M-1), `Propiedad` (M-1), `CustomUser` (M-1).
| `PreAutorizacion` | `visitas` | Credencial previa generada por residentes. | `CustomUser` (M-1), `Propiedad` (M-1).

## 🛠️ Stack Tecnológico
- **Backend:** Python + Django.
- **Frontend:** HTML, CSS y JavaScript vanilla con utilidades de Django templates.
- **Base de datos:** SQLite por defecto (configurable a otros motores).
- **Dependencias clave:** ver `requirements.txt` para versiones exactas.

## ⚙️ Puesta en Marcha
```bash
# 1. Clonar
git clone git@github.com:RichardAgapito/App-Gesti-n-Residencias.git
cd App-Gesti-n-Residencias

# 2. Entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Base de datos
python manage.py migrate

# 5. Usuario admin
python manage.py createsuperuser

# 6. Server de desarrollo
python manage.py runserver
```
El proyecto queda disponible en `http://127.0.0.1:8000/`.

## 🧱 Estructura de Apps
- `complejos`: lógica de negocio para complejos, propiedades, amenidades, reservas y contratos.
- `users`: perfiles extendidos, roles y autenticación.
- `visitas`: registro de visitantes, pre-autorizaciones y panel del guardia.
- `templates` y `static`: recursos compartidos para todo el proyecto.

## ✅ Calidad y Roadmap
**Bugs recientes corregidos**
1. Iconos de navegación en calendarios restaurados tras conflicto de `font-weight`.
2. Paneles de bloqueo ahora listan y permiten desbloquear horarios (admin) y muestran disponibilidad real (residentes).
3. Nueva función `isDayFullyBooked` y clases CSS para marcar días sin cupo.
4. Corrección de desfase horario al estandarizar el formato de fecha entre Django y JS.
5. Validación backend en formularios de reservas y bloqueos para respetar horarios de amenidades.
6. Renderizado consistente de mensajes de error en plantillas.

**Próximas mejoras sugeridas**
- Refactorizar estilos embebidos a hojas `.css` dedicadas.
- Migrar permisos a grupos/permissions nativos de Django.
- Exponer una API con Django Rest Framework para futuros frontends/mobile.
- Ampliar la cobertura de tests unitarios e integraciones críticas.
- Generar códigos QR para accesos en la app `visitas`.
- Preparar internacionalización (i18n) completa.

## 🤝 Contribuir
1. Crea un branch descriptivo.
2. Ejecuta lint/tests relevantes.
3. Abre un PR detallando cambios, pruebas y capturas si aplica.

Siempre se agradecen issues con contexto y pasos para reproducir.
