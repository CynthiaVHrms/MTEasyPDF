# MTEasyPDF Web

## Technical Documentation

---

# Información del Documento

| Campo              | Valor                      |
| ------------------ | -------------------------- |
| Proyecto           | MTEasyPDF Web              |
| Organización       | HEMAC Automation Engine    |
| Tipo de documento  | Documentación Técnica      |
| Versión            | 1.0.0                      |
| Estado             | En desarrollo              |
| Fecha              | Junio 2026                 |
| Lenguaje Backend   | Python 3.13                |
| Framework Backend  | FastAPI                    |
| Lenguaje Frontend  | TypeScript                 |
| Framework Frontend | Next.js 16                 |
| Arquitectura       | Cliente - Servidor         |
| Elaborado por      | Equipo de Desarrollo HEMAC |

---

# Tabla de Contenido

1. Introducción
2. Objetivo del Proyecto
3. Alcance
4. Arquitectura General
5. Arquitectura Backend
6. Arquitectura Frontend
7. Flujo General del Sistema
8. Componentes del Sistema
9. Estructura del Repositorio
10. Tecnologías Utilizadas
11. Flujo de Generación del PDF
12. API REST
13. Manejo de Archivos
14. Variables de Entorno
15. Seguridad
16. Manejo de Errores
17. Rendimiento
18. Escalabilidad
19. Convenciones del Proyecto
20. Roadmap
21. Conclusiones

---

# 1. Introducción

MTEasyPDF Web es la evolución del sistema de escritorio desarrollado originalmente para el área de Automatización de HEMAC.

La aplicación tiene como objetivo automatizar la generación de memorias técnicas a partir de información proporcionada por el usuario y un conjunto de evidencias contenidas en un archivo ZIP.

El sistema reemplaza completamente la ejecución manual realizada anteriormente mediante una aplicación de escritorio, ofreciendo una arquitectura moderna basada en tecnologías web.

Actualmente el sistema permite:

* Captura de información del proyecto.
* Carga de imágenes personalizadas.
* Carga de evidencias comprimidas.
* Generación automática del PDF.
* Creación automática del ZIP final.
* Descarga directa desde navegador.
* Hipervínculos funcionales hacia anexos.
* Interfaz completamente web.

---

# 2. Objetivo del Proyecto

El objetivo principal es proporcionar una plataforma web capaz de generar documentación técnica de manera automática, reduciendo considerablemente el tiempo requerido para elaborar memorias técnicas de proyectos.

El sistema busca:

* Reducir errores humanos.
* Automatizar tareas repetitivas.
* Centralizar la generación documental.
* Facilitar futuras ampliaciones.
* Modernizar la herramienta existente.

---

# 3. Alcance

La versión actual contempla las siguientes funcionalidades.

## Backend

* API REST mediante FastAPI.
* Recepción de formularios multipart/form-data.
* Validación de archivos.
* Procesamiento del ZIP.
* Extracción automática.
* Generación del PDF.
* Generación del ZIP final.
* Descarga del resultado.

## Frontend

* Aplicación desarrollada con Next.js.
* Formularios modernos.
* Validación básica.
* Carga de archivos.
* Comunicación con la API.
* Descarga del ZIP.

---

# 4. Arquitectura General

El sistema sigue una arquitectura Cliente-Servidor.

```text
                Usuario
                   │
                   ▼
        Navegador Web (Next.js)
                   │
        HTTP / REST API
                   │
                   ▼
           FastAPI Backend
                   │
    ┌──────────────┼───────────────┐
    ▼              ▼               ▼
PDF Engine   File Engine   Storage Service
    │              │               │
    └──────────────┼───────────────┘
                   ▼
          Reporte Principal
                   │
                   ▼
           ZIP Final Generado
```

Esta arquitectura permite separar completamente la interfaz gráfica del motor encargado de construir los documentos PDF.

---

# 5. Principios de Arquitectura

Durante el desarrollo del proyecto se siguieron los siguientes principios:

* Separación de responsabilidades.
* Modularidad.
* Bajo acoplamiento.
* Alta cohesión.
* Código reutilizable.
* Fácil mantenimiento.
* Escalabilidad.
* Configuración mediante variables de entorno.

---

# 6. Arquitectura Backend

El backend está construido sobre FastAPI.

Su responsabilidad consiste en recibir la petición del frontend, validar la información, generar el reporte y devolver el archivo final.

La estructura principal es:

```text
backend/

app/

api/
routes/

core/

schemas/

services/

workers/

pdf_engine/

tests/
```

Cada módulo posee responsabilidades claramente definidas.

### api/

Contiene todos los endpoints REST.

### core/

Configuraciones generales.

Variables de entorno.

Configuraciones de seguridad.

### schemas/

Modelos Pydantic.

Validaciones.

### services/

Lógica de negocio.

Procesamiento de archivos.

Creación de carpetas temporales.

Compresión.

### workers/

Procesos pesados.

Generación del PDF.

### pdf_engine/

Motor completo de generación documental.

---

# 7. Arquitectura Frontend

El frontend fue desarrollado con Next.js 16 utilizando App Router.

Su principal responsabilidad consiste en servir como interfaz para el usuario.

Estructura principal:

```text
frontend/

app/

components/

features/

reports/
```

Se siguió una organización basada en componentes reutilizables.

---

# 8. Flujo General del Sistema

```text
Usuario

↓

Llena formulario

↓

Selecciona imágenes

↓

Selecciona ZIP

↓

Enviar

↓

FastAPI

↓

Valida datos

↓

Extrae ZIP

↓

Genera PDF

↓

Genera hipervínculos

↓

Construye ZIP Final

↓

Devuelve download_url

↓

Frontend

↓

Usuario descarga resultado
```

---

# 9. Tecnologías Utilizadas

## Backend

* Python 3.13
* FastAPI
* Uvicorn
* Pydantic
* Pillow
* ReportLab
* zipfile
* pathlib

## Frontend

* Next.js 16
* React
* TypeScript
* Tailwind CSS
* Fetch API

---

# 10. Variables de Entorno

Backend

```text
.env
```

Variables previstas:

```text
OUTPUT_DIRECTORY=

TEMP_DIRECTORY=

LOG_LEVEL=

HOST=

PORT=
```

Frontend

```text
.env.local
```

Variables:

```text
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

---

# 11. API REST

Actualmente el sistema expone los siguientes endpoints.

## Generar Reporte

POST

```text
/reports/generate
```

Recibe:

* título
* información extra
* introducción
* imágenes
* ZIP

Devuelve:

```json
{
  "job_id":"",
  "status":"",
  "download_url":"",
  "zip_path":""
}
```

---

## Descargar Resultado

GET

```text
/reports/{job_id}/download
```

Devuelve el ZIP final generado.

---

# 12. Manejo de Archivos

El sistema utiliza directorios temporales para cada trabajo generado.

Cada ejecución produce un Job independiente.

```text
jobs/

job_id/

input/

output/

temp/
```

Esto evita conflictos entre múltiples usuarios.

---

# 13. Seguridad

Actualmente el sistema implementa:

* Validación de extensiones.
* Validación de archivos obligatorios.
* Directorios temporales aislados.

En futuras versiones se incorporará:

* Active Directory.
* JWT.
* HTTPS.
* Control de permisos.

---

# 14. Rendimiento

Actualmente el procesamiento es síncrono.

La siguiente versión migrará a:

* Celery.
* Redis.
* Cola de trabajos.
* Procesamiento en segundo plano.

---

# 15. Escalabilidad

El proyecto fue diseñado para crecer mediante módulos independientes.

Las futuras funcionalidades incluyen:

* Historial de reportes.
* Gestión de usuarios.
* Active Directory.
* Dashboard administrativo.
* Notificaciones.
* Registro de auditoría.
* Docker.
* Integración CI/CD.

---

# 16. Convenciones del Proyecto

* snake_case para Python.
* PascalCase para componentes React.
* camelCase para variables TypeScript.
* Tipado estricto.
* Separación entre lógica y presentación.

---

# 17. Roadmap

Versión 1.0

* ✔ Backend FastAPI.
* ✔ Frontend Next.js.
* ✔ Generación PDF.
* ✔ Descarga ZIP.
* ✔ Hipervínculos funcionales.

Versión 2.0

* Active Directory.
* Celery.
* Redis.
* Historial.
* Dashboard.

Versión 3.0

* Multiusuario.
* Auditoría.
* Estadísticas.
* Administración.

---

# 18. Conclusiones

MTEasyPDF Web representa la modernización del sistema de generación de memorias técnicas utilizado dentro de HEMAC.

La arquitectura implementada permite mantener una clara separación entre la interfaz web, la lógica de negocio y el motor de generación documental, facilitando su mantenimiento y evolución.

La adopción de tecnologías modernas como FastAPI, Next.js y TypeScript proporciona una base sólida para futuras funcionalidades empresariales, incluyendo autenticación corporativa, procesamiento asíncrono y despliegues automatizados.
