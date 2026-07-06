import shutil
import traceback
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.protocols_escudo_c5.folder_generator import generate_folders_from_excel
from app.protocols_escudo_c5.document_generator import generate_protocol_document

router = APIRouter(prefix="/protocols", tags=["Protocols"])

@router.post("/folders/generate")
async def generate_protocol_folders(
    excel_file: UploadFile = File(...),
):
    filename = excel_file.filename or ""

    if not filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="El archivo debe ser un Excel válido con extensión .xlsx o .xls.",
        )

    protocols_dir = settings.storage_dir / "protocols"
    input_dir = protocols_dir / "input"

    input_dir.mkdir(parents=True, exist_ok=True)

    excel_path = input_dir / "informacion_sitios.xlsx"

    try:
        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(excel_file.file, buffer)

        result = generate_folders_from_excel(
            excel_path=excel_path,
            work_dir=protocols_dir,
            sheet_name="Hoja2",
        )

        return FileResponse(
            path=result.zip_path,
            filename="Estructura_Carpetas_C5.zip",
            media_type="application/zip",
            headers={
                "X-Job-Id": result.job_id,
                "X-Total-Enlaces": str(result.total_enlaces),
                "X-Total-Sitios": str(result.total_sitios),
                "X-Total-Clasificaciones": str(result.total_clasificaciones),
            },
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generando estructura de carpetas: {exc}",
        )


@router.post("/document/generate")
async def generate_protocol_document_endpoint(
    excel_file: UploadFile = File(...),
    evidence_zip: UploadFile = File(...),
):
    excel_filename = excel_file.filename or ""
    evidence_filename = evidence_zip.filename or ""

    if not excel_filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(
            status_code=400,
            detail="El archivo de información debe ser un Excel .xlsx o .xls.",
        )

    if not evidence_filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="El archivo de evidencias debe ser un ZIP.",
        )

    protocols_dir = settings.storage_dir / "protocols"
    input_dir = protocols_dir / "document_input"

    input_dir.mkdir(parents=True, exist_ok=True)

    excel_path = input_dir / "informacion_sitios.xlsx"
    evidence_zip_path = input_dir / "evidencias.zip"

    template_docx_path = (
        Path(__file__).resolve().parents[2]
        / "protocols_escudo_c5"
        / "templates"
        / "plantilla_protocolo_c5.docx"
    )

    if not template_docx_path.exists():
        raise HTTPException(
            status_code=500,
            detail=f"No se encontró la plantilla oficial Word en: {template_docx_path}",
        )

    try:
        with open(excel_path, "wb") as buffer:
            shutil.copyfileobj(excel_file.file, buffer)

        with open(evidence_zip_path, "wb") as buffer:
            shutil.copyfileobj(evidence_zip.file, buffer)

        result = generate_protocol_document(
            excel_path=excel_path,
            evidence_zip_path=evidence_zip_path,
            template_docx_path=template_docx_path,
            work_dir=protocols_dir / "documents",
        )

        return FileResponse(
            path=result.output_docx_path,
            filename="Protocolo_C5_Generado.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "X-Job-Id": result.job_id,
                "X-Total-Sitios": str(result.total_sitios),
                "X-Total-Documentos-Generados": str(
                    result.total_documentos_generados
                ),
            },
        )

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generando protocolo Word: {exc}",
        )



# @router.post("/document/generate")
# async def generate_protocol_document_endpoint(
#     excel_file: UploadFile = File(...),
#     evidence_zip: UploadFile = File(...),
#     template_docx: UploadFile = File(...),
# ):
#     excel_filename = excel_file.filename or ""
#     evidence_filename = evidence_zip.filename or ""
#     template_filename = template_docx.filename or ""

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

#     if not template_filename.lower().endswith(".docx"):
#         raise HTTPException(
#             status_code=400,
#             detail="La plantilla debe ser un documento Word .docx.",
#         )

#     protocols_dir = settings.storage_dir / "protocols"
#     input_dir = protocols_dir / "document_input"

#     input_dir.mkdir(parents=True, exist_ok=True)

#     excel_path = input_dir / "informacion_sitios.xlsx"
#     evidence_zip_path = input_dir / "evidencias.zip"
#     template_docx_path = input_dir / "plantilla.docx"

#     try:
#         with open(excel_path, "wb") as buffer:
#             shutil.copyfileobj(excel_file.file, buffer)

#         with open(evidence_zip_path, "wb") as buffer:
#             shutil.copyfileobj(evidence_zip.file, buffer)

#         with open(template_docx_path, "wb") as buffer:
#             shutil.copyfileobj(template_docx.file, buffer)

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

