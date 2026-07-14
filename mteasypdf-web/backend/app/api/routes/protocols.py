from __future__ import annotations

import json
import re
import shutil
import traceback
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.protocols_escudo_c5.document_generator import (
    generate_protocol_document,
)
from app.protocols_escudo_c5.folder_generator import (
    generate_folders_from_excel,
)


router = APIRouter(prefix="/protocols", tags=["Protocols"])

ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}
JOB_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
DIAGNOSTICS_FILENAME = "diagnostico_generacion.json"


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


def create_request_directory(process_name: str) -> tuple[str, Path]:
    """Crea una carpeta independiente para cada solicitud concurrente."""

    request_id = uuid4().hex
    request_dir = (
        Path(settings.storage_dir)
        / "protocols"
        / "request_uploads"
        / process_name
        / request_id
    )
    request_dir.mkdir(parents=True, exist_ok=False)

    return request_id, request_dir


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


def get_document_diagnostics_path(job_id: str) -> Path:
    """Devuelve la ruta segura del diagnóstico asociado a un trabajo."""

    normalized_job_id = job_id.strip().lower()

    if not JOB_ID_PATTERN.fullmatch(normalized_job_id):
        raise HTTPException(
            status_code=400,
            detail="El identificador del proceso no es válido.",
        )

    return (
        Path(settings.storage_dir)
        / "protocols"
        / "document_jobs"
        / normalized_job_id
        / "o"
        / DIAGNOSTICS_FILENAME
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
        payload = json.loads(
            diagnostics_path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible leer el diagnóstico de la generación.",
        ) from exc

    return JSONResponse(content=payload)


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
    protocols_dir = Path(settings.storage_dir) / "protocols"

    try:
        save_upload(upload=excel_file, destination=excel_path)

        result = generate_folders_from_excel(
            excel_path=excel_path,
            work_dir=protocols_dir / "folder_jobs",
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


@router.post("/document/generate")
async def generate_protocol_document_endpoint(
    excel_file: UploadFile = File(...),
    evidence_zip: UploadFile = File(...),
):
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
    protocols_dir = Path(settings.storage_dir) / "protocols"

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

        result = generate_protocol_document(
            excel_path=excel_path,
            evidence_zip_path=evidence_zip_path,
            template_docx_path=template_docx_path,
            work_dir=protocols_dir / "document_jobs",
        )

        return FileResponse(
            path=result.output_docx_path,
            filename="Protocolo_C5_Generado.docx",
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            ),
            headers={
                "X-Request-Id": request_id,
                "X-Job-Id": result.job_id,
                "X-Total-Sitios": str(result.total_sitios),
                "X-Total-Documentos-Generados": str(
                    result.total_documentos_generados
                ),
                # Compatibilidad defensiva: si operativa conserva una versión
                # anterior de ProtocolDocumentResult, la descarga no debe fallar
                # por un encabezado informativo.
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

# import shutil
# import traceback
# from pathlib import Path
# from uuid import uuid4

# from fastapi import APIRouter, File, HTTPException, UploadFile
# from fastapi.responses import FileResponse

# from app.core.config import settings
# from app.protocols_escudo_c5.document_generator import (
#     generate_protocol_document,
# )
# from app.protocols_escudo_c5.folder_generator import (
#     generate_folders_from_excel,
# )


# router = APIRouter(prefix="/protocols", tags=["Protocols"])

# ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}


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
#                 "X-Total-Imagenes-Omitidas": str(
#                     result.total_imagenes_omitidas
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
