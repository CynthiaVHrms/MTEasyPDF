from __future__ import annotations

import shutil
import traceback
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.core.config import settings
from app.protocols_escudo_c5.document_generator import (
    generate_protocol_document,
)
from app.protocols_escudo_c5.folder_generator import (
    generate_folders_from_excel,
)


router = APIRouter(prefix="/protocols", tags=["Protocols"])

ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}


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
                "X-Total-Imagenes-Omitidas": str(
                    result.total_imagenes_omitidas
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










# import shutil
# import traceback
# from pathlib import Path

# from fastapi import APIRouter, UploadFile, File, HTTPException
# from fastapi.responses import FileResponse

# from app.core.config import settings
# from app.protocols_escudo_c5.folder_generator import generate_folders_from_excel
# from app.protocols_escudo_c5.document_generator import generate_protocol_document

# router = APIRouter(prefix="/protocols", tags=["Protocols"])

# @router.post("/folders/generate")
# async def generate_protocol_folders(
#     excel_file: UploadFile = File(...),
# ):
#     filename = excel_file.filename or ""

#     if not filename.lower().endswith((".xlsx", ".xls")):
#         raise HTTPException(
#             status_code=400,
#             detail="El archivo debe ser un Excel válido con extensión .xlsx o .xls.",
#         )

#     protocols_dir = settings.storage_dir / "protocols"
#     input_dir = protocols_dir / "input"

#     input_dir.mkdir(parents=True, exist_ok=True)

#     excel_path = input_dir / "informacion_sitios.xlsx"

#     try:
#         with open(excel_path, "wb") as buffer:
#             shutil.copyfileobj(excel_file.file, buffer)

#         result = generate_folders_from_excel(
#             excel_path=excel_path,
#             work_dir=protocols_dir,
#             sheet_name="Hoja2",
#         )

#         return FileResponse(
#             path=result.zip_path,
#             filename="Estructura_Carpetas_C5.zip",
#             media_type="application/zip",
#             headers={
#                 "X-Job-Id": result.job_id,
#                 "X-Total-Enlaces": str(result.total_enlaces),
#                 "X-Total-Sitios": str(result.total_sitios),
#                 "X-Total-Clasificaciones": str(result.total_clasificaciones),
#             },
#         )

#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc))

#     except Exception as exc:
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error generando estructura de carpetas: {exc}",
#         )


# @router.post("/document/generate")
# async def generate_protocol_document_endpoint(
#     excel_file: UploadFile = File(...),
#     evidence_zip: UploadFile = File(...),
# ):
#     excel_filename = excel_file.filename or ""
#     evidence_filename = evidence_zip.filename or ""

#     if not excel_filename.lower().endswith((".xlsx", ".xls")):
#         raise HTTPException(
#             status_code=400,
#             detail="El archivo de información debe ser un Excel .xlsx o .xls.",
#         )

#     if not evidence_filename.lower().endswith(".zip"):
#         raise HTTPException(
#             status_code=400,
#             detail="El archivo de evidencias debe ser un ZIP.",
#         )

#     protocols_dir = settings.storage_dir / "protocols"
#     input_dir = protocols_dir / "document_input"

#     input_dir.mkdir(parents=True, exist_ok=True)

#     excel_path = input_dir / "informacion_sitios.xlsx"
#     evidence_zip_path = input_dir / "evidencias.zip"

#     template_docx_path = (
#         Path(__file__).resolve().parents[2]
#         / "protocols_escudo_c5"
#         / "templates"
#         / "plantilla_protocolo_c5.docx"
#     )

#     if not template_docx_path.exists():
#         raise HTTPException(
#             status_code=500,
#             detail=f"No se encontró la plantilla oficial Word en: {template_docx_path}",
#         )

#     try:
#         with open(excel_path, "wb") as buffer:
#             shutil.copyfileobj(excel_file.file, buffer)

#         with open(evidence_zip_path, "wb") as buffer:
#             shutil.copyfileobj(evidence_zip.file, buffer)

#         result = generate_protocol_document(
#             excel_path=excel_path,
#             evidence_zip_path=evidence_zip_path,
#             template_docx_path=template_docx_path,
#             work_dir=protocols_dir / "documents",
#         )

#         return FileResponse(
#             path=result.output_docx_path,
#             filename="Protocolo_C5_Generado.docx",
#             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
#             headers={
#                 "X-Job-Id": result.job_id,
#                 "X-Total-Sitios": str(result.total_sitios),
#                 "X-Total-Documentos-Generados": str(
#                     result.total_documentos_generados
#                 ),
#             },
#         )

#     except ValueError as exc:
#         raise HTTPException(status_code=400, detail=str(exc))

#     except Exception as exc:
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error generando protocolo Word: {exc}",
#         )

