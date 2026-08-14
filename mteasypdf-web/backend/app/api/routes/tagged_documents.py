from __future__ import annotations

import json
import os
import shutil
import tempfile
import traceback

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.protocols_escudo_c5.document_editor import (
    TAGGED_OUTPUT_DOCX_FILENAME,
    TAG_STRUCTURE_ZIP_FILENAME,
    generate_document_from_tags,
    generate_tagged_document_folders,
)
from app.protocols_escudo_c5.tag_validation import (
    format_validation_error,
    validate_word_and_excel_tags,
)


router = APIRouter(
    prefix="/protocols/document-tags-v2",
    tags=["Protocolos C5 - completar Word"],
)


WORD_MEDIA_TYPE = (
    "application/"
    "vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def max_upload_size_bytes() -> int:
    return settings.max_upload_size_mb * 1024 * 1024


def max_upload_size_label() -> str:
    return f"{settings.max_upload_size_mb} MB"


def storage_root() -> Path:
    configured_path = (
        os.getenv("MTEASYPDF_STORAGE_DIR", "").strip()
        or str(settings.storage_dir)
    )

    if configured_path:
        root = Path(configured_path)
    else:
        root = Path(tempfile.gettempdir()) / "mteasypdf_jobs"

    root.mkdir(parents=True, exist_ok=True)
    return root


def tagged_folder_jobs_dir() -> Path:
    path = storage_root() / "protocols" / "tagged_folder_jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def tagged_document_jobs_dir() -> Path:
    path = storage_root() / "protocols" / "tagged_document_jobs"
    path.mkdir(parents=True, exist_ok=True)
    return path




def tagged_diagnostics_path(job_id: str) -> Path:
    if not job_id or any(character not in "0123456789abcdef" for character in job_id.lower()):
        raise HTTPException(status_code=400, detail="El identificador del trabajo no es válido.")

    path = tagged_document_jobs_dir() / job_id / "o" / "diagnostico_etiquetas.json"

    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="No se encontró el diagnóstico del documento solicitado.")

    return path


def create_request_directory(
    operation_name: str,
) -> tuple[str, Path]:
    request_id = uuid4().hex
    request_dir = (
        storage_root()
        / "requests"
        / operation_name
        / request_id
    )
    (request_dir / "input").mkdir(parents=True, exist_ok=True)
    return request_id, request_dir


async def save_upload(
    upload: UploadFile,
    destination: Path,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    total_written = 0
    limit_bytes = max_upload_size_bytes()

    try:
        with destination.open("wb") as output_file:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total_written += len(chunk)
                if total_written > limit_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "El archivo "
                            f"{upload.filename or 'seleccionado'} "
                            "supera el tamaño máximo permitido "
                            f"({max_upload_size_label()})."
                        ),
                    )
                output_file.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "No fue posible guardar temporalmente "
                f"el archivo {upload.filename or 'seleccionado'}."
            ),
        ) from exc


def validate_excel_filename(filename: str) -> str:
    extension = Path(filename).suffix.lower()

    if extension not in {".xlsx", ".xls"}:
        raise HTTPException(
            status_code=400,
            detail=(
                "El formato de etiquetas debe ser un archivo "
                "Excel .xlsx o .xls."
            ),
        )

    return extension


def validate_word_filename(filename: str) -> None:
    if Path(filename).suffix.lower() != ".docx":
        raise HTTPException(
            status_code=400,
            detail=(
                "El documento incompleto debe ser un "
                "archivo Word .docx."
            ),
        )


def validate_zip_filename(filename: str) -> None:
    if Path(filename).suffix.lower() != ".zip":
        raise HTTPException(
            status_code=400,
            detail=(
                "Las evidencias deben enviarse dentro "
                "de un archivo ZIP."
            ),
        )


@router.post("/validate")
async def validate_tagged_document(
    excel_file: UploadFile = File(...),
    tagged_document: UploadFile = File(...),
):
    excel_filename = excel_file.filename or ""
    word_filename = tagged_document.filename or ""

    excel_extension = validate_excel_filename(excel_filename)
    validate_word_filename(word_filename)

    request_id, request_dir = create_request_directory(
        "tag_validation"
    )

    input_dir = request_dir / "input"
    excel_path = input_dir / f"etiquetas{excel_extension}"
    word_path = input_dir / "documento_incompleto.docx"

    try:
        await save_upload(excel_file, excel_path)
        await save_upload(tagged_document, word_path)

        result = validate_word_and_excel_tags(
            document_path=word_path,
            excel_path=excel_path,
        )

        response = result.to_dict()
        response["request_id"] = request_id
        return response

    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=(
                "Ocurrió un error inesperado al validar "
                f"las etiquetas: {exc}"
            ),
        ) from exc
    finally:
        await excel_file.close()
        await tagged_document.close()
        shutil.rmtree(request_dir, ignore_errors=True)


@router.post("/folders/generate")
async def generate_tagged_folders(
    excel_file: UploadFile = File(...),
):
    excel_filename = excel_file.filename or ""
    excel_extension = validate_excel_filename(excel_filename)

    request_id, request_dir = create_request_directory(
        "tagged_folder_generation_v2"
    )

    excel_path = request_dir / "input" / f"etiquetas{excel_extension}"

    try:
        await save_upload(excel_file, excel_path)

        result = generate_tagged_document_folders(
            excel_path=excel_path,
            work_dir=tagged_folder_jobs_dir(),
        )

        return FileResponse(
            path=result.zip_path,
            filename=TAG_STRUCTURE_ZIP_FILENAME,
            media_type="application/zip",
            headers={
                "X-Request-Id": request_id,
                "X-Job-Id": result.job_id,
                "X-Total-Etiquetas": str(result.total_tags),
                "X-Total-Evidencias": str(result.total_evidences),
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
            detail=(
                "Error generando la estructura "
                f"de carpetas por etiqueta: {exc}"
            ),
        ) from exc
    finally:
        await excel_file.close()
        shutil.rmtree(request_dir, ignore_errors=True)


@router.post("/generate")
async def generate_validated_tagged_document(
    excel_file: UploadFile = File(...),
    tagged_document: UploadFile = File(...),
    evidence_zip: UploadFile = File(...),
):
    excel_filename = excel_file.filename or ""
    word_filename = tagged_document.filename or ""
    zip_filename = evidence_zip.filename or ""

    excel_extension = validate_excel_filename(excel_filename)
    validate_word_filename(word_filename)
    validate_zip_filename(zip_filename)

    request_id, request_dir = create_request_directory(
        "tagged_document_generation_v2"
    )

    input_dir = request_dir / "input"
    excel_path = input_dir / f"etiquetas{excel_extension}"
    word_path = input_dir / "documento_incompleto.docx"
    zip_path = input_dir / "evidencias.zip"

    try:
        await save_upload(excel_file, excel_path)
        await save_upload(tagged_document, word_path)
        await save_upload(evidence_zip, zip_path)

        validation = validate_word_and_excel_tags(
            document_path=word_path,
            excel_path=excel_path,
        )

        if not validation.compatible:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": format_validation_error(validation),
                    "validation": validation.to_dict(),
                },
            )

        result = generate_document_from_tags(
            excel_path=excel_path,
            tagged_document_path=word_path,
            evidence_zip_path=zip_path,
            work_dir=tagged_document_jobs_dir(),
        )

        return FileResponse(
            path=result.output_docx_path,
            filename=TAGGED_OUTPUT_DOCX_FILENAME,
            media_type=WORD_MEDIA_TYPE,
            headers={
                "X-Request-Id": request_id,
                "X-Job-Id": result.job_id,
                "X-Total-Etiquetas": str(result.total_tags),
                "X-Total-Etiquetas-Reemplazadas": str(
                    result.total_tags_replaced
                ),
                "X-Total-Etiquetas-No-Encontradas": str(
                    result.total_tags_not_found
                ),
                "X-Total-Imagenes-Insertadas": str(
                    result.total_images_inserted
                ),
                "X-Total-Imagenes-No-Encontradas": str(
                    result.total_images_missing
                ),
                "X-Total-Imagenes-Omitidas": str(
                    result.total_images_omitted
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
            detail=(
                "Ocurrió un error inesperado al completar "
                f"el documento Word: {exc}"
            ),
        ) from exc
    finally:
        await excel_file.close()
        await tagged_document.close()
        await evidence_zip.close()
        shutil.rmtree(request_dir, ignore_errors=True)


@router.get("/{job_id}/diagnostics")
async def get_tagged_document_diagnostics(job_id: str):
    diagnostics_path = tagged_diagnostics_path(job_id)

    try:
        payload = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="No fue posible leer el diagnóstico del documento.",
        ) from exc

    return JSONResponse(content=payload)





# from __future__ import annotations

# import os
# import shutil
# import tempfile
# import traceback

# from pathlib import Path
# from uuid import uuid4

# from fastapi import APIRouter, File, HTTPException, UploadFile
# from fastapi.responses import FileResponse

# from app.protocols_escudo_c5.document_editor import (
#     TAGGED_OUTPUT_DOCX_FILENAME,
#     TAG_STRUCTURE_ZIP_FILENAME,
#     generate_document_from_tags,
#     generate_tagged_document_folders,
# )
# from app.protocols_escudo_c5.tag_validation import (
#     format_validation_error,
#     validate_word_and_excel_tags,
# )


# router = APIRouter(
#     prefix="/protocols/document-tags-v2",
#     tags=["Protocolos C5 - completar Word"],
# )


# WORD_MEDIA_TYPE = (
#     "application/"
#     "vnd.openxmlformats-officedocument.wordprocessingml.document"
# )


# def storage_root() -> Path:
#     configured_path = os.getenv(
#         "MTEASYPDF_STORAGE_DIR",
#         "",
#     ).strip()

#     if configured_path:
#         root = Path(configured_path)
#     else:
#         root = (
#             Path(tempfile.gettempdir())
#             / "mteasypdf_jobs"
#         )

#     root.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     return root


# def tagged_folder_jobs_dir() -> Path:
#     path = (
#         storage_root()
#         / "protocols"
#         / "tagged_folder_jobs"
#     )

#     path.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     return path


# def tagged_document_jobs_dir() -> Path:
#     path = (
#         storage_root()
#         / "protocols"
#         / "tagged_document_jobs"
#     )

#     path.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     return path


# def create_request_directory(
#     operation_name: str,
# ) -> tuple[str, Path]:
#     request_id = uuid4().hex

#     request_dir = (
#         storage_root()
#         / "requests"
#         / operation_name
#         / request_id
#     )

#     (request_dir / "input").mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     return request_id, request_dir


# async def save_upload(
#     upload: UploadFile,
#     destination: Path,
# ) -> None:
#     destination.parent.mkdir(
#         parents=True,
#         exist_ok=True,
#     )

#     try:
#         with destination.open("wb") as output_file:
#             while True:
#                 chunk = await upload.read(
#                     1024 * 1024,
#                 )

#                 if not chunk:
#                     break

#                 output_file.write(chunk)

#     except OSError as exc:
#         raise HTTPException(
#             status_code=500,
#             detail=(
#                 "No fue posible guardar temporalmente "
#                 f"el archivo {upload.filename or 'seleccionado'}."
#             ),
#         ) from exc


# def validate_excel_filename(
#     filename: str,
# ) -> str:
#     extension = Path(filename).suffix.lower()

#     if extension not in {".xlsx", ".xls"}:
#         raise HTTPException(
#             status_code=400,
#             detail=(
#                 "El formato de etiquetas debe ser un archivo "
#                 "Excel .xlsx o .xls."
#             ),
#         )

#     return extension


# def validate_word_filename(
#     filename: str,
# ) -> None:
#     if Path(filename).suffix.lower() != ".docx":
#         raise HTTPException(
#             status_code=400,
#             detail=(
#                 "El documento incompleto debe ser un "
#                 "archivo Word .docx."
#             ),
#         )


# def validate_zip_filename(
#     filename: str,
# ) -> None:
#     if Path(filename).suffix.lower() != ".zip":
#         raise HTTPException(
#             status_code=400,
#             detail=(
#                 "Las evidencias deben enviarse dentro "
#                 "de un archivo ZIP."
#             ),
#         )


# @router.post("/validate")
# async def validate_tagged_document(
#     excel_file: UploadFile = File(...),
#     tagged_document: UploadFile = File(...),
# ):
#     """
#     Compara las etiquetas escritas en el Word con las etiquetas del Excel.

#     No modifica el documento.
#     """

#     excel_filename = excel_file.filename or ""
#     word_filename = tagged_document.filename or ""

#     excel_extension = validate_excel_filename(
#         excel_filename
#     )
#     validate_word_filename(
#         word_filename
#     )

#     request_id, request_dir = create_request_directory(
#         "tag_validation"
#     )

#     input_dir = request_dir / "input"
#     excel_path = (
#         input_dir
#         / f"etiquetas{excel_extension}"
#     )
#     word_path = (
#         input_dir
#         / "documento_incompleto.docx"
#     )

#     try:
#         await save_upload(
#             upload=excel_file,
#             destination=excel_path,
#         )

#         await save_upload(
#             upload=tagged_document,
#             destination=word_path,
#         )

#         result = validate_word_and_excel_tags(
#             document_path=word_path,
#             excel_path=excel_path,
#         )

#         response = result.to_dict()
#         response["request_id"] = request_id

#         return response

#     except HTTPException:
#         raise

#     except ValueError as exc:
#         raise HTTPException(
#             status_code=400,
#             detail=str(exc),
#         ) from exc

#     except Exception as exc:
#         traceback.print_exc()

#         raise HTTPException(
#             status_code=500,
#             detail=(
#                 "Ocurrió un error inesperado al validar "
#                 f"las etiquetas: {exc}"
#             ),
#         ) from exc

#     finally:
#         await excel_file.close()
#         await tagged_document.close()

#         shutil.rmtree(
#             request_dir,
#             ignore_errors=True,
#         )


# @router.post("/folders/generate")
# async def generate_tagged_folders(
#     excel_file: UploadFile = File(...),
# ):
#     """
#     Genera el ZIP vacío de carpetas a partir del Excel de etiquetas.
#     """

#     excel_filename = excel_file.filename or ""

#     excel_extension = validate_excel_filename(
#         excel_filename
#     )

#     request_id, request_dir = create_request_directory(
#         "tagged_folder_generation_v2"
#     )

#     excel_path = (
#         request_dir
#         / "input"
#         / f"etiquetas{excel_extension}"
#     )

#     try:
#         await save_upload(
#             upload=excel_file,
#             destination=excel_path,
#         )

#         result = generate_tagged_document_folders(
#             excel_path=excel_path,
#             work_dir=tagged_folder_jobs_dir(),
#         )

#         return FileResponse(
#             path=result.zip_path,
#             filename=TAG_STRUCTURE_ZIP_FILENAME,
#             media_type="application/zip",
#             headers={
#                 "X-Request-Id": request_id,
#                 "X-Job-Id": result.job_id,
#                 "X-Total-Etiquetas": str(
#                     result.total_tags
#                 ),
#                 "X-Total-Evidencias": str(
#                     result.total_evidences
#                 ),
#             },
#         )

#     except HTTPException:
#         raise

#     except ValueError as exc:
#         raise HTTPException(
#             status_code=400,
#             detail=str(exc),
#         ) from exc

#     except Exception as exc:
#         traceback.print_exc()

#         raise HTTPException(
#             status_code=500,
#             detail=(
#                 "Error generando la estructura "
#                 f"de carpetas por etiqueta: {exc}"
#             ),
#         ) from exc

#     finally:
#         await excel_file.close()

#         shutil.rmtree(
#             request_dir,
#             ignore_errors=True,
#         )


# @router.post("/generate")
# async def generate_validated_tagged_document(
#     excel_file: UploadFile = File(...),
#     tagged_document: UploadFile = File(...),
#     evidence_zip: UploadFile = File(...),
# ):
#     """
#     Valida Word y Excel antes de generar el documento final.

#     La generación no comienza cuando:
#     - Falta una etiqueta en Word.
#     - Falta una etiqueta en Excel.
#     - Una etiqueta aparece repetida en Word.
#     """

#     excel_filename = excel_file.filename or ""
#     word_filename = tagged_document.filename or ""
#     zip_filename = evidence_zip.filename or ""

#     excel_extension = validate_excel_filename(
#         excel_filename
#     )
#     validate_word_filename(
#         word_filename
#     )
#     validate_zip_filename(
#         zip_filename
#     )

#     request_id, request_dir = create_request_directory(
#         "tagged_document_generation_v2"
#     )

#     input_dir = request_dir / "input"

#     excel_path = (
#         input_dir
#         / f"etiquetas{excel_extension}"
#     )
#     word_path = (
#         input_dir
#         / "documento_incompleto.docx"
#     )
#     zip_path = (
#         input_dir
#         / "evidencias.zip"
#     )

#     try:
#         await save_upload(
#             upload=excel_file,
#             destination=excel_path,
#         )

#         await save_upload(
#             upload=tagged_document,
#             destination=word_path,
#         )

#         await save_upload(
#             upload=evidence_zip,
#             destination=zip_path,
#         )

#         validation = validate_word_and_excel_tags(
#             document_path=word_path,
#             excel_path=excel_path,
#         )

#         if not validation.compatible:
#             raise HTTPException(
#                 status_code=422,
#                 detail={
#                     "message": format_validation_error(
#                         validation
#                     ),
#                     "validation": validation.to_dict(),
#                 },
#             )

#         result = generate_document_from_tags(
#             excel_path=excel_path,
#             tagged_document_path=word_path,
#             evidence_zip_path=zip_path,
#             work_dir=tagged_document_jobs_dir(),
#         )

#         return FileResponse(
#             path=result.output_docx_path,
#             filename=TAGGED_OUTPUT_DOCX_FILENAME,
#             media_type=WORD_MEDIA_TYPE,
#             headers={
#                 "X-Request-Id": request_id,
#                 "X-Job-Id": result.job_id,
#                 "X-Total-Etiquetas": str(
#                     result.total_tags
#                 ),
#                 "X-Total-Etiquetas-Reemplazadas": str(
#                     result.total_tags_replaced
#                 ),
#                 "X-Total-Etiquetas-No-Encontradas": str(
#                     result.total_tags_not_found
#                 ),
#                 "X-Total-Imagenes-Insertadas": str(
#                     result.total_images_inserted
#                 ),
#                 "X-Total-Imagenes-No-Encontradas": str(
#                     result.total_images_missing
#                 ),
#                 "X-Total-Imagenes-Omitidas": str(
#                     result.total_images_omitted
#                 ),
#             },
#         )

#     except HTTPException:
#         raise

#     except ValueError as exc:
#         raise HTTPException(
#             status_code=400,
#             detail=str(exc),
#         ) from exc

#     except Exception as exc:
#         traceback.print_exc()

#         raise HTTPException(
#             status_code=500,
#             detail=(
#                 "Ocurrió un error inesperado al completar "
#                 f"el documento Word: {exc}"
#             ),
#         ) from exc

#     finally:
#         await excel_file.close()
#         await tagged_document.close()
#         await evidence_zip.close()

#         shutil.rmtree(
#             request_dir,
#             ignore_errors=True,
#         )