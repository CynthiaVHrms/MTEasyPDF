# CHANGELOG

Todos los cambios importantes realizados en **MTEasyPDF Web** serán documentados en este archivo.

Este proyecto sigue una adaptación del estándar **Keep a Changelog**, permitiendo llevar un historial claro de la evolución del sistema.

---

# Información General

| Campo               | Valor                  |
| ------------------- | ---------------------- |
| Proyecto            | MTEasyPDF Web          |
| Organización        | HEMAC                  |
| Tipo                | Historial de Versiones |
| Inicio del Proyecto | 2026                   |
| Estado              | En desarrollo          |

---

# Versionado

El proyecto utiliza el esquema de versionado semántico:

```text
MAJOR.MINOR.PATCH
```

Donde:

* **MAJOR** → Cambios incompatibles o grandes rediseños.
* **MINOR** → Nuevas funcionalidades compatibles.
* **PATCH** → Correcciones de errores y mejoras menores.

Ejemplos:

```text
1.0.0
1.1.0
1.2.3
2.0.0
```

---

# v1.0.0 — Primera Versión Web

**Fecha:** Junio 2026

## Descripción

Primera versión funcional de **MTEasyPDF Web**, resultado de la migración de la aplicación de escritorio desarrollada originalmente en Python hacia una arquitectura web moderna basada en FastAPI y Next.js.

---

## Added

### Backend

* Implementación de API REST utilizando FastAPI.
* Arquitectura modular basada en servicios.
* Motor de generación PDF desacoplado.
* Procesamiento de archivos ZIP.
* Extracción automática de evidencias.
* Organización automática de anexos.
* Generación de Reporte Principal.
* Generación automática del ZIP final.
* Directorios temporales por Job.
* Endpoint para descarga del archivo generado.
* Documentación automática mediante Swagger.

### Frontend

* Desarrollo de interfaz con Next.js.
* Implementación de TypeScript.
* Uso de Tailwind CSS.
* Formulario moderno para captura de información.
* Carga de imágenes.
* Carga de ZIP de evidencias.
* Comunicación con API REST.
* Descarga del ZIP final desde navegador.
* Diseño responsivo.

### Motor PDF

* Migración del código de escritorio.
* Compatibilidad con ReportLab.
* Compatibilidad con PyPDF2.
* Inserción automática de portada.
* Inserción de logotipos institucionales.
* Organización por secciones.
* Organización por categorías.
* Generación de índice.
* Inserción de anexos.
* Hipervínculos hacia documentación técnica.

### Documentación

* Inicio de documentación técnica.
* Creación de README profesional.
* Creación de CHANGELOG.
* Planeación del nuevo Manual de Usuario.

---

## Changed

* Migración completa de aplicación Desktop a arquitectura Web.
* Separación entre Frontend y Backend.
* Eliminación de dependencias de interfaz de escritorio.
* Refactorización del motor PDF.
* Nueva estructura del repositorio.
* Incorporación de variables de entorno.
* Implementación de almacenamiento temporal por trabajos.

---

## Fixed

Durante el desarrollo de la migración se resolvieron, entre otros, los siguientes problemas:

* Corrección de rutas de Windows durante la extracción del ZIP.
* Compatibilidad con carpetas que contienen espacios.
* Compatibilidad con nombres de archivos largos.
* Corrección en la clasificación de imágenes.
* Corrección en la organización de documentación técnica.
* Eliminación de errores de importación del motor PDF.
* Corrección de funciones de agrupación de mantenimiento.
* Corrección de la comunicación Frontend ↔ Backend.
* Configuración de CORS para desarrollo local.
* Corrección de inserción de logotipos institucionales.
* Corrección de enlaces a anexos dentro del ZIP generado.
* Eliminación de duplicados en la copia de anexos.

---

## Security

* Validación de archivos ZIP recibidos.
* Validación de imágenes cargadas por el usuario.
* Directorios temporales aislados por Job.
* Eliminación automática de archivos temporales al finalizar el procesamiento.

---

## Known Issues

La versión actual presenta las siguientes limitaciones conocidas:

* El procesamiento de grandes volúmenes de información aún es síncrono.
* No existe autenticación de usuarios.
* No se implementa aún Active Directory.
* No existe historial de reportes generados.
* No se cuenta con panel administrativo.
* Docker aún no forma parte de la distribución oficial.

---

# Próxima Versión

## v1.1.0

Objetivos principales:

### Backend

* Procesamiento asíncrono con Celery.
* Redis para cola de trabajos.
* Mejoras de rendimiento.
* Optimización del procesamiento de archivos grandes.

### Frontend

* Indicador de progreso en tiempo real.
* Mejora de la experiencia de usuario.
* Integración del componente de documentación.
* Descarga del Manual de Usuario desde la aplicación.

### Documentación

* Finalización del Manual de Usuario.
* Publicación de la Documentación Técnica completa.
* Inclusión de diagramas de arquitectura.
* Actualización del README.

---

# Roadmap

## Versión 2.0

* Integración con Active Directory.
* Gestión de usuarios.
* Historial de reportes.
* Dashboard administrativo.
* Registro de auditoría.

---

## Versión 3.0

* Contenedorización mediante Docker.
* Despliegue en producción.
* Balanceo de carga.
* Integración continua (CI/CD).
* Monitoreo y observabilidad.

---

# Notas

Cada nueva versión del proyecto deberá actualizar este archivo antes de su liberación.

El historial de cambios forma parte de la documentación oficial de MTEasyPDF Web y sirve como referencia para desarrolladores, administradores y personal de soporte.
