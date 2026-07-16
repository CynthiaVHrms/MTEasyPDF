from __future__ import annotations

import json
import shutil
import traceback

from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.protocols_escudo_c5.document_generator import (
    ProtocolDocumentResult,
    generate_protocol_document,
)
from app.protocols_escudo_c5.folder_generator import (
    generate_folders_from_excel,
)
from app.protocols_escudo_c5.progress_store import (
    create_job_status,
    read_job_status,
    update_job_status,
    validate_job_id,
)


router = APIRouter(prefix="/protocols", tags=["Protocols"])

ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
DIAGNOSTICS_FILENAME = "diagnostico_generacion.json"
WORD_FILENAME = "Protocolo_C5_Generado.docx"
WORD_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "wordprocessingml.document"
)


def protocols_dir() -> Path:
    return Path(settings.storage_dir) / "protocols"


def document_jobs_dir() -> Path:
    return protocols_dir() / "document_jobs"


def document_status_dir() -> Path:
    return protocols_dir() / "document_job_status"


def validate_excel_filename(filename: str) -> str:
    """Valida el nombre del Excel y devuelve su extensión normalizada."""

    extension = Path(filename).suffix.lower()

    if extension not in ALLOWED_EXCEL_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "El archivo debe ser un Excel válido con extensión "
                ".xlsx o .xls."
            ),
        )

    return extension


def normalize_job_id(job_id: str) -> str:
    try:
        return validate_job_id(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def create_request_directory(
    process_name: str,
    request_id: str | None = None,
) -> tuple[str, Path]:
    """Crea una carpeta independiente para cada solicitud concurrente."""

    normalized_request_id = request_id or uuid4().hex
    request_dir = (
        protocols_dir()
        / "request_uploads"
        / process_name
        / normalized_request_id
    )
    request_dir.mkdir(parents=True, exist_ok=False)

    return normalized_request_id, request_dir


def save_upload(upload: UploadFile, destination: Path) -> None:
    """Guarda un archivo recibido por FastAPI en la carpeta de la solicitud."""

    destination.parent.mkdir(parents=True, exist_ok=True)
    upload.file.seek(0)

    with destination.open("wb") as output_file:
        shutil.copyfileobj(
            upload.file,
            output_file,
            length=1024 * 1024,
        )

    if not destination.exists() or destination.stat().st_size == 0:
        raise ValueError("El archivo recibido está vacío.")


def get_document_output_path(job_id: str) -> Path:
    normalized_job_id = normalize_job_id(job_id)
    return document_jobs_dir() / normalized_job_id / "o" / WORD_FILENAME


def get_document_diagnostics_path(job_id: str) -> Path:
    normalized_job_id = normalize_job_id(job_id)
    return (
        document_jobs_dir()
        / normalized_job_id
        / "o"
        / DIAGNOSTICS_FILENAME
    )


def _progress_callback_for(job_id: str):
    def publish(payload: dict[str, object]) -> None:
        update_job_status(
            document_status_dir(),
            job_id,
            status="processing",
            **payload,
        )

    return publish


def _run_protocol_document_job(
    *,
    job_id: str,
    request_dir: Path,
    excel_path: Path,
    evidence_zip_path: Path,
    template_docx_path: Path,
) -> None:
    """Procesa un documento en segundo plano y publica su avance real."""

    try:
        update_job_status(
            document_status_dir(),
            job_id,
            status="processing",
            stage="validating_files",
            percentage=2,
            message="El servidor recibió los archivos. Iniciando la validación.",
        )

        result = generate_protocol_document(
            excel_path=excel_path,
            evidence_zip_path=evidence_zip_path,
            template_docx_path=template_docx_path,
            work_dir=document_jobs_dir(),
            job_id=job_id,
            progress_callback=_progress_callback_for(job_id),
        )

        diagnostics_ready = bool(
            result.diagnostics_path
            and result.diagnostics_path.exists()
            and result.diagnostics_path.is_file()
        )

        update_job_status(
            document_status_dir(),
            job_id,
            status="completed",
            stage="completed",
            percentage=100,
            message=(
                "Documento Word generado correctamente. "
                "La descarga está lista."
            ),
            current_site=result.total_sitios,
            total_sites=result.total_sitios,
            download_ready=True,
            diagnostics_ready=diagnostics_ready,
            error=None,
        )

    except ValueError as exc:
        current = read_job_status(document_status_dir(), job_id) or {}
        update_job_status(
            document_status_dir(),
            job_id,
            status="failed",
            stage="failed",
            percentage=current.get("percentage", 0),
            message="No fue posible generar el documento.",
            download_ready=False,
            diagnostics_ready=False,
            error=str(exc),
        )

    except Exception as exc:
        traceback.print_exc()
        current = read_job_status(document_status_dir(), job_id) or {}
        update_job_status(
            document_status_dir(),
            job_id,
            status="failed",
            stage="failed",
            percentage=current.get("percentage", 0),
            message="La generación se detuvo por un error inesperado.",
            download_ready=False,
            diagnostics_ready=False,
            error=(
                "Ocurrió un error inesperado al generar el protocolo Word. "
                f"Detalle: {exc}"
            ),
        )

    finally:
        shutil.rmtree(request_dir, ignore_errors=True)


@router.get("/document/{job_id}/status")
async def get_protocol_document_status(job_id: str):
    """Devuelve el avance actual de un trabajo de generación Word."""

    normalized_job_id = normalize_job_id(job_id)
    payload = read_job_status(document_status_dir(), normalized_job_id)

    if payload is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "No se encontró el proceso solicitado. Es posible que haya "
                "expirado o que el servidor se haya reiniciado."
            ),
        )

    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/document/{job_id}/download")
async def download_protocol_document(job_id: str):
    """Descarga el documento cuando el trabajo terminó correctamente."""

    normalized_job_id = normalize_job_id(job_id)
    status_payload = read_job_status(document_status_dir(), normalized_job_id)

    if status_payload is None:
        raise HTTPException(
            status_code=404,
            detail="No se encontró el proceso solicitado.",
        )

    if status_payload.get("status") == "failed":
        raise HTTPException(
            status_code=409,
            detail=(
                status_payload.get("error")
                or "La generación del documento terminó con error."
            ),
        )

    if status_payload.get("status") != "completed":
        raise HTTPException(
            status_code=409,
            detail="El documento todavía se está generando.",
        )

    output_path = get_document_output_path(normalized_job_id)

    if not output_path.exists() or not output_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="El documento final ya no se encuentra disponible.",
        )

    return FileResponse(
        path=output_path,
        filename=WORD_FILENAME,
        media_type=WORD_MEDIA_TYPE,
    )


@router.get("/document/{job_id}/diagnostics")
async def get_protocol_document_diagnostics(job_id: str):
    """Entrega el resumen de evidencias faltantes de una generación Word."""

    diagnostics_path = get_document_diagnostics_path(job_id)

    if not diagnostics_path.exists() or not diagnostics_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=(
                "No se encontró el diagnóstico de esta generación. "
                "Es posible que el proceso haya expirado o que pertenezca "
                "a una versión anterior del sistema."
            ),
        )

    try:
        payload = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible leer el diagnóstico de la generación.",
        ) from exc

    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/folders/generate")
async def generate_protocol_folders(
    excel_file: UploadFile = File(...),
):
    excel_filename = excel_file.filename or ""
    excel_extension = validate_excel_filename(excel_filename)

    request_id, request_dir = create_request_directory("folder_generation")
    excel_path = (
        request_dir
        / "input"
        / f"informacion_sitios{excel_extension}"
    )

    try:
        save_upload(upload=excel_file, destination=excel_path)

        result = generate_folders_from_excel(
            excel_path=excel_path,
            work_dir=protocols_dir() / "folder_jobs",
            sheet_name="Hoja2",
        )

        return FileResponse(
            path=result.zip_path,
            filename="Estructura_Carpetas_C5.zip",
            media_type="application/zip",
            headers={
                "X-Request-Id": request_id,
                "X-Job-Id": result.job_id,
                "X-Total-Enlaces": str(result.total_enlaces),
                "X-Total-Sitios": str(result.total_sitios),
                "X-Total-Clasificaciones": str(
                    result.total_clasificaciones
                ),
            },
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generando la estructura de carpetas: {exc}",
        ) from exc

    finally:
        await excel_file.close()
        shutil.rmtree(request_dir, ignore_errors=True)


@router.post("/document/jobs", status_code=202)
async def create_protocol_document_job(
    background_tasks: BackgroundTasks,
    excel_file: UploadFile = File(...),
    evidence_zip: UploadFile = File(...),
):
    """Recibe archivos, crea un trabajo y responde sin esperar el Word."""

    excel_filename = excel_file.filename or ""
    evidence_filename = evidence_zip.filename or ""
    excel_extension = validate_excel_filename(excel_filename)

    if Path(evidence_filename).suffix.lower() != ".zip":
        raise HTTPException(
            status_code=400,
            detail="El archivo de evidencias debe ser un ZIP.",
        )

    job_id = uuid4().hex
    _, request_dir = create_request_directory(
        "document_generation_jobs",
        request_id=job_id,
    )
    input_dir = request_dir / "input"
    excel_path = input_dir / f"informacion_sitios{excel_extension}"
    evidence_zip_path = input_dir / "evidencias.zip"

    template_docx_path = (
        Path(__file__).resolve().parents[2]
        / "protocols_escudo_c5"
        / "templates"
        / "plantilla_protocolo_c5.docx"
    )

    try:
        if not template_docx_path.exists():
            raise HTTPException(
                status_code=500,
                detail=(
                    "No se encontró la plantilla oficial Word en: "
                    f"{template_docx_path}"
                ),
            )

        save_upload(upload=excel_file, destination=excel_path)
        save_upload(upload=evidence_zip, destination=evidence_zip_path)

        create_job_status(
            document_status_dir(),
            job_id,
            message=(
                "Archivos recibidos. El documento está en espera de iniciar."
            ),
        )

        background_tasks.add_task(
            _run_protocol_document_job,
            job_id=job_id,
            request_dir=request_dir,
            excel_path=excel_path,
            evidence_zip_path=evidence_zip_path,
            template_docx_path=template_docx_path,
        )

        return {
            "job_id": job_id,
            "status": "queued",
            "status_url": f"/protocols/document/{job_id}/status",
            "download_url": f"/protocols/document/{job_id}/download",
            "diagnostics_url": (
                f"/protocols/document/{job_id}/diagnostics"
            ),
        }

    except HTTPException:
        shutil.rmtree(request_dir, ignore_errors=True)
        raise

    except ValueError as exc:
        shutil.rmtree(request_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        shutil.rmtree(request_dir, ignore_errors=True)
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"No fue posible iniciar la generación: {exc}",
        ) from exc

    finally:
        await excel_file.close()
        await evidence_zip.close()


@router.post("/document/generate")
async def generate_protocol_document_endpoint(
    excel_file: UploadFile = File(...),
    evidence_zip: UploadFile = File(...),
):
    """Endpoint síncrono conservado por compatibilidad con integraciones previas."""

    excel_filename = excel_file.filename or ""
    evidence_filename = evidence_zip.filename or ""
    excel_extension = validate_excel_filename(excel_filename)

    if Path(evidence_filename).suffix.lower() != ".zip":
        raise HTTPException(
            status_code=400,
            detail="El archivo de evidencias debe ser un ZIP.",
        )

    request_id, request_dir = create_request_directory("document_generation")
    input_dir = request_dir / "input"
    excel_path = input_dir / f"informacion_sitios{excel_extension}"
    evidence_zip_path = input_dir / "evidencias.zip"

    template_docx_path = (
        Path(__file__).resolve().parents[2]
        / "protocols_escudo_c5"
        / "templates"
        / "plantilla_protocolo_c5.docx"
    )

    if not template_docx_path.exists():
        shutil.rmtree(request_dir, ignore_errors=True)
        raise HTTPException(
            status_code=500,
            detail=(
                "No se encontró la plantilla oficial Word en: "
                f"{template_docx_path}"
            ),
        )

    try:
        save_upload(upload=excel_file, destination=excel_path)
        save_upload(upload=evidence_zip, destination=evidence_zip_path)

        result: ProtocolDocumentResult = generate_protocol_document(
            excel_path=excel_path,
            evidence_zip_path=evidence_zip_path,
            template_docx_path=template_docx_path,
            work_dir=document_jobs_dir(),
        )

        return FileResponse(
            path=result.output_docx_path,
            filename=WORD_FILENAME,
            media_type=WORD_MEDIA_TYPE,
            headers={
                "X-Request-Id": request_id,
                "X-Job-Id": result.job_id,
                "X-Total-Sitios": str(result.total_sitios),
                "X-Total-Documentos-Generados": str(
                    result.total_documentos_generados
                ),
                "X-Total-Imagenes-Omitidas": str(
                    getattr(result, "total_imagenes_omitidas", 0)
                ),
                "X-Total-Imagenes-No-Encontradas": str(
                    getattr(result, "total_imagenes_no_encontradas", 0)
                ),
                "X-Total-Clasificaciones-No-Encontradas": str(
                    getattr(
                        result,
                        "total_clasificaciones_no_encontradas",
                        0,
                    )
                ),
            },
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generando el protocolo Word: {exc}",
        ) from exc

    finally:
        await excel_file.close()
        await evidence_zip.close()
        shutil.rmtree(request_dir, ignore_errors=True)















# from __future__ import annotations

# import json
# import re
# import shutil
# import traceback
# from pathlib import Path
# from uuid import uuid4

# from fastapi import APIRouter, File, HTTPException, UploadFile
# from fastapi.responses import FileResponse, JSONResponse

# from app.core.config import settings
# from app.protocols_escudo_c5.document_generator import (
#     generate_protocol_document,
# )
# from app.protocols_escudo_c5.folder_generator import (
#     generate_folders_from_excel,
# )


# router = APIRouter(prefix="/protocols", tags=["Protocols"])

# ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
# JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
# DIAGNOSTICS_FILENAME = "diagnostico_generacion.json"


# def validate_excel_filename(filename: str) -> str:
#     """Valida el nombre del Excel y devuelve su extensión normalizada."""

#     extension = Path(filename).suffix.lower()

#     if extension not in ALLOWED_EXCEL_EXTENSIONS:
#         raise HTTPException(
#             status_code=400,
#             detail=(
#                 "El archivo debe ser un Excel válido con extensión "
#                 ".xlsx o .xls."
#             ),
#         )

#     return extension


# def create_request_directory(process_name: str) -> tuple[str, Path]:
#     """Crea una carpeta independiente para cada solicitud concurrente."""

#     request_id = uuid4().hex
#     request_dir = (
#         Path(settings.storage_dir)
#         / "protocols"
#         / "request_uploads"
#         / process_name
#         / request_id
#     )
#     request_dir.mkdir(parents=True, exist_ok=False)

#     return request_id, request_dir


# def save_upload(upload: UploadFile, destination: Path) -> None:
#     """Guarda un archivo recibido por FastAPI en la carpeta de la solicitud."""

#     destination.parent.mkdir(parents=True, exist_ok=True)
#     upload.file.seek(0)

#     with destination.open("wb") as output_file:
#         shutil.copyfileobj(
#             upload.file,
#             output_file,
#             length=1024 * 1024,
#         )

#     if not destination.exists() or destination.stat().st_size == 0:
#         raise ValueError("El archivo recibido está vacío.")


# def get_document_diagnostics_path(job_id: str) -> Path:
#     """Devuelve la ruta segura del diagnóstico asociado a un trabajo."""

#     normalized_job_id = job_id.strip().lower()

#     if not JOB_ID_PATTERN.fullmatch(normalized_job_id):
#         raise HTTPException(
#             status_code=400,
#             detail="El identificador del proceso no es válido.",
#         )

#     return (
#         Path(settings.storage_dir)
#         / "protocols"
#         / "document_jobs"
#         / normalized_job_id
#         / "o"
#         / DIAGNOSTICS_FILENAME
#     )


# @router.get("/document/{job_id}/diagnostics")
# async def get_protocol_document_diagnostics(job_id: str):
#     """Entrega el resumen de evidencias faltantes de una generación Word."""

#     diagnostics_path = get_document_diagnostics_path(job_id)

#     if not diagnostics_path.exists() or not diagnostics_path.is_file():
#         raise HTTPException(
#             status_code=404,
#             detail=(
#                 "No se encontró el diagnóstico de esta generación. "
#                 "Es posible que el proceso haya expirado o que pertenezca "
#                 "a una versión anterior del sistema."
#             ),
#         )

#     try:
#         payload = json.loads(
#             diagnostics_path.read_text(encoding="utf-8")
#         )
#     except (OSError, json.JSONDecodeError) as exc:
#         raise HTTPException(
#             status_code=500,
#             detail="No fue posible leer el diagnóstico de la generación.",
#         ) from exc

#     return JSONResponse(content=payload)


# @router.post("/folders/generate")
# async def generate_protocol_folders(
#     excel_file: UploadFile = File(...),
# ):
#     excel_filename = excel_file.filename or ""
#     excel_extension = validate_excel_filename(excel_filename)

#     request_id, request_dir = create_request_directory("folder_generation")
#     excel_path = (
#         request_dir
#         / "input"
#         / f"informacion_sitios{excel_extension}"
#     )
#     protocols_dir = Path(settings.storage_dir) / "protocols"

#     try:
#         save_upload(upload=excel_file, destination=excel_path)

#         result = generate_folders_from_excel(
#             excel_path=excel_path,
#             work_dir=protocols_dir / "folder_jobs",
#             sheet_name="Hoja2",
#         )

#         return FileResponse(
#             path=result.zip_path,
#             filename="Estructura_Carpetas_C5.zip",
#             media_type="application/zip",
#             headers={
#                 "X-Request-Id": request_id,
#                 "X-Job-Id": result.job_id,
#                 "X-Total-Enlaces": str(result.total_enlaces),
#                 "X-Total-Sitios": str(result.total_sitios),
#                 "X-Total-Clasificaciones": str(
#                     result.total_clasificaciones
#                 ),
#             },
#         )

#     except HTTPException:
#         raise

#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc)) from exc

#     except Exception as exc:
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error generando la estructura de carpetas: {exc}",
#         ) from exc

#     finally:
#         await excel_file.close()
#         shutil.rmtree(request_dir, ignore_errors=True)


# @router.post("/document/generate")
# async def generate_protocol_document_endpoint(
#     excel_file: UploadFile = File(...),
#     evidence_zip: UploadFile = File(...),
# ):
#     excel_filename = excel_file.filename or ""
#     evidence_filename = evidence_zip.filename or ""

#     excel_extension = validate_excel_filename(excel_filename)

#     if Path(evidence_filename).suffix.lower() != ".zip":
#         raise HTTPException(
#             status_code=400,
#             detail="El archivo de evidencias debe ser un ZIP.",
#         )

#     request_id, request_dir = create_request_directory("document_generation")
#     input_dir = request_dir / "input"
#     excel_path = input_dir / f"informacion_sitios{excel_extension}"
#     evidence_zip_path = input_dir / "evidencias.zip"
#     protocols_dir = Path(settings.storage_dir) / "protocols"

#     template_docx_path = (
#         Path(__file__).resolve().parents[2]
#         / "protocols_escudo_c5"
#         / "templates"
#         / "plantilla_protocolo_c5.docx"
#     )

#     if not template_docx_path.exists():
#         shutil.rmtree(request_dir, ignore_errors=True)
#         raise HTTPException(
#             status_code=500,
#             detail=(
#                 "No se encontró la plantilla oficial Word en: "
#                 f"{template_docx_path}"
#             ),
#         )

#     try:
#         save_upload(upload=excel_file, destination=excel_path)
#         save_upload(upload=evidence_zip, destination=evidence_zip_path)

#         result = generate_protocol_document(
#             excel_path=excel_path,
#             evidence_zip_path=evidence_zip_path,
#             template_docx_path=template_docx_path,
#             work_dir=protocols_dir / "document_jobs",
#         )

#         return FileResponse(
#             path=result.output_docx_path,
#             filename="Protocolo_C5_Generado.docx",
#             media_type=(
#                 "application/vnd.openxmlformats-officedocument."
#                 "wordprocessingml.document"
#             ),
#             headers={
#                 "X-Request-Id": request_id,
#                 "X-Job-Id": result.job_id,
#                 "X-Total-Sitios": str(result.total_sitios),
#                 "X-Total-Documentos-Generados": str(
#                     result.total_documentos_generados
#                 ),
#                 # Compatibilidad defensiva: si operativa conserva una versión
#                 # anterior de ProtocolDocumentResult, la descarga no debe fallar
#                 # por un encabezado informativo.
#                 "X-Total-Imagenes-Omitidas": str(
#                     getattr(result, "total_imagenes_omitidas", 0)
#                 ),
#                 "X-Total-Imagenes-No-Encontradas": str(
#                     getattr(result, "total_imagenes_no_encontradas", 0)
#                 ),
#                 "X-Total-Clasificaciones-No-Encontradas": str(
#                     getattr(
#                         result,
#                         "total_clasificaciones_no_encontradas",
#                         0,
#                     )
#                 ),
#             },
#         )

#     except HTTPException:
#         raise

#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc)) from exc

#     except Exception as exc:
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error generando el protocolo Word: {exc}",
#         ) from exc

#     finally:
#         await excel_file.close()
#         await evidence_zip.close()
#         shutil.rmtree(request_dir, ignore_errors=True)














