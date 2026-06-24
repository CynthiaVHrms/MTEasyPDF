# MTEasyPDF Web

> **Modernización de la plataforma MTEasyPDF mediante una arquitectura Web basada en FastAPI y Next.js.**

---

# Descripción

**MTEasyPDF Web** es una aplicación desarrollada para **HEMAC** cuyo propósito es automatizar la generación de Memorias Técnicas a partir de evidencias organizadas en un archivo ZIP.

La plataforma es la evolución de la aplicación de escritorio desarrollada originalmente en Python, migrando hacia una arquitectura Web moderna, escalable y mantenible.

Actualmente el sistema permite:

* Generación automática de Memorias Técnicas.
* Procesamiento de archivos ZIP.
* Inserción automática de imágenes.
* Organización de anexos.
* Generación de hipervínculos internos.
* Descarga automática del ZIP final.
* Interfaz Web moderna y responsiva.

---

# Objetivos

El proyecto tiene como objetivo principal:

* Reducir tiempos de generación documental.
* Estandarizar la elaboración de Memorias Técnicas.
* Eliminar procesos manuales.
* Facilitar el mantenimiento futuro del sistema.
* Preparar la plataforma para nuevas funcionalidades empresariales.

---

# Arquitectura General

```text
                    Usuario
                       │
                       ▼
             Frontend (Next.js)
                       │
                 HTTP / REST API
                       │
                       ▼
              Backend (FastAPI)
                       │
      ┌────────────────┼────────────────┐
      ▼                ▼                ▼
 PDF Engine      File Engine      Storage Service
      │                │                │
      └────────────────┼────────────────┘
                       ▼
              Reporte Principal
                       │
                       ▼
               ZIP Final de Entrega
```

---

# Tecnologías

## Backend

* Python 3.13
* FastAPI
* Uvicorn
* Pydantic
* ReportLab
* PyPDF2
* Pillow

## Frontend

* Next.js 16
* React
* TypeScript
* Tailwind CSS

## Herramientas

* Git
* GitHub
* Visual Studio Code
* Docker *(fase futura)*

---

# Estructura del Proyecto

```text
mteasypdf-web/

backend/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── pdf_engine/
│   ├── schemas/
│   ├── services/
│   └── workers/
│
└── tests/

frontend/
│
├── app/
├── components/
└── features/

docs/
│
├── TECHNICAL_DOCUMENTATION.md
├── MANUAL_USUARIO.md
├── CHANGELOG.md
└── assets/

docker-compose.yml
```

---

# Flujo General

```text
Usuario

↓

Captura información

↓

Selecciona imágenes

↓

Selecciona ZIP

↓

Enviar

↓

FastAPI

↓

Procesamiento

↓

Motor PDF

↓

ZIP Final

↓

Descarga
```

---

# Requisitos

## Backend

* Python 3.13 o superior

## Frontend

* Node.js 22 LTS o superior
* npm 10 o superior

---

# Variables de Entorno

## Backend

Crear:

```text
backend/.env
```

Ejemplo:

```env
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO
```

---

## Frontend

Crear:

```text
frontend/.env.local
```

Contenido:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

---

# Instalación

## 1. Clonar repositorio

```bash
git clone <repositorio>
```

---

## 2. Backend

```bash
cd backend

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

API:

```
http://127.0.0.1:8000
```

Swagger:

```
http://127.0.0.1:8000/docs
```

---

## 3. Frontend

```bash
cd frontend

npm install

npm run dev
```

Aplicación:

```
http://localhost:3000
```

---

# Documentación

La documentación oficial del proyecto se encuentra en la carpeta:

```text
docs/
```

Documentos disponibles:

* TECHNICAL_DOCUMENTATION.md
* MANUAL_USUARIO.md
* CHANGELOG.md

---

# Estado del Proyecto

Versión actual:

```
v1.0.0
```

Estado:

```
En desarrollo
```

---

# Roadmap

## Versión 1.0

* Backend FastAPI
* Frontend Next.js
* Motor PDF
* Descarga del ZIP
* Hipervínculos funcionales

---

## Versión 2.0

* Active Directory
* Celery
* Redis
* Historial de reportes
* Dashboard administrativo

---

## Versión 3.0

* Gestión de usuarios
* Auditoría
* Estadísticas
* Docker
* Despliegue productivo

---

# Buenas Prácticas

Durante el desarrollo del proyecto se siguen los siguientes principios:

* Clean Architecture
* Principios SOLID
* Código desacoplado
* Componentes reutilizables
* Tipado estricto
* Modularidad
* Escalabilidad
* Mantenibilidad

---

# Equipo del Proyecto

Proyecto desarrollado para **HEMAC** como parte del proceso de modernización de la herramienta MTEasyPDF.

---

# Licencia

Uso interno para HEMAC.

Todos los derechos reservados.

---

# Contacto

Para dudas relacionadas con el proyecto, consultar la documentación técnica disponible en la carpeta `docs/` o contactar al equipo responsable del mantenimiento del sistema.
