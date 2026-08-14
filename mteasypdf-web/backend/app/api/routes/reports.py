import shutil
import traceback
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.core.config import settings
from app.protocols_escudo_c5.progress_store import (
    create_job_status,
    read_job_status,
    update_job_status,
    validate_job_id,
)
from app.services.storage_service import StorageService
from app.pdf_engine.generator import generate_report
from app.pdf_engine.models import ReportGenerationRequest


router = APIRouter(prefix="/reports", tags=["Reports"])
storage = StorageService()


def max_upload_size_bytes() -> int:
    return settings.max_upload_size_mb * 1024 * 1024


def max_upload_size_label() -> str:
    return f"{settings.max_upload_size_mb} MB"


def reports_status_dir() -> Path:
    return settings.storage_dir / "reports" / "job_status"


def normalize_job_id(job_id: str) -> str:
    try:
        return validate_job_id(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def save_limited_upload_file(
    upload_file: UploadFile,
    path: Path,
) -> str:
    total_written = 0
    limit_bytes = max_upload_size_bytes()

    try:
        with open(path, "wb") as buffer:
            while True:
                chunk = upload_file.file.read(1024 * 1024)
                if not chunk:
                    break

                total_written += len(chunk)
                if total_written > limit_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "El archivo "
                            f"{upload_file.filename or 'seleccionado'} "
                            "supera el tamaño máximo permitido "
                            f"({max_upload_size_label()})."
                        ),
                    )

                buffer.write(chunk)
    except HTTPException:
        path.unlink(missing_ok=True)
        raise

    return str(path)


def save_upload_file(upload_file: UploadFile | None, path: Path) -> str:
    if not upload_file or not upload_file.filename:
        return ""

    return save_limited_upload_file(upload_file, path)


def build_project_data(
    *,
    titulo: str,
    info_extra: str,
    introduccion: str,
    portada_path: str,
    logo_sup_izq_path: str,
    logo_sup_der_path: str,
    logo_inf_izq_path: str,
    logo_inf_der_path: str,
) -> dict[str, str]:
    return {
        "titulo": titulo,
        "info_extra": info_extra,
        "introduccion": introduccion,
        "imagen_portada": portada_path,
        "logo_sup_izq": logo_sup_izq_path,
        "logo_sup_der": logo_sup_der_path,
        "logo_inf_izq": logo_inf_izq_path,
        "logo_inf_der": logo_inf_der_path,
    }


def _run_report_job(
    *,
    job_id: str,
    zip_path: Path,
    output_dir: Path,
    temp_dir: Path,
    project_data: dict[str, str],
    usa_ubicacion: bool,
) -> None:
    try:
        update_job_status(
            reports_status_dir(),
            job_id,
            status="processing",
            stage="processing",
            percentage=15,
            message="Generando memoria técnica. Este proceso puede tardar varios minutos.",
            download_ready=False,
            error=None,
        )

        request = ReportGenerationRequest(
            job_id=job_id,
            zip_path=zip_path,
            output_dir=output_dir,
            temp_dir=temp_dir,
            project_data=project_data,
            usa_ubicacion=usa_ubicacion,
        )

        result = generate_report(request)

        update_job_status(
            reports_status_dir(),
            job_id,
            status="completed",
            stage="completed",
            percentage=100,
            message="Memoria técnica generada correctamente.",
            download_ready=True,
            zip_path=str(result.final_zip_path),
            error=None,
        )

    except ValueError as exc:
        current = read_job_status(reports_status_dir(), job_id) or {}
        update_job_status(
            reports_status_dir(),
            job_id,
            status="failed",
            stage="failed",
            percentage=current.get("percentage", 0),
            message="No fue posible generar el reporte.",
            download_ready=False,
            error=str(exc),
        )
    except Exception as exc:
        traceback.print_exc()
        current = read_job_status(reports_status_dir(), job_id) or {}
        update_job_status(
            reports_status_dir(),
            job_id,
            status="failed",
            stage="failed",
            percentage=current.get("percentage", 0),
            message="La generación se detuvo por un error inesperado.",
            download_ready=False,
            error=(
                "Ocurrió un error inesperado al generar la memoria técnica. "
                f"Detalle: {exc}"
            ),
        )


@router.post("/generate")
async def generate_report_endpoint(
    titulo: str = Form(...),
    info_extra: str = Form(""),
    introduccion: str = Form(""),
    usa_ubicacion: bool = Form(True),

    imagen_portada: UploadFile | None = File(None),

    logo_sup_izq: UploadFile | None = File(None),
    logo_sup_der: UploadFile | None = File(None),
    logo_inf_izq: UploadFile | None = File(None),
    logo_inf_der: UploadFile | None = File(None),

    evidencias_zip: UploadFile = File(...),
):
    if not evidencias_zip.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="El archivo de evidencias debe ser un ZIP.",
        )

    job_id = storage.create_job_id()
    dirs = storage.prepare_job_dirs(job_id)

    input_dir: Path = dirs["input_dir"]
    temp_dir: Path = dirs["temp_dir"]
    output_dir: Path = dirs["output_dir"]

    zip_path = input_dir / "evidencias.zip"

    save_limited_upload_file(evidencias_zip, zip_path)

    portada_path = save_upload_file(
        imagen_portada,
        input_dir / "portada.png",
    )

    logo_sup_izq_path = save_upload_file(
        logo_sup_izq,
        input_dir / "logo_sup_izq.png",
    )

    logo_sup_der_path = save_upload_file(
        logo_sup_der,
        input_dir / "logo_sup_der.png",
    )

    logo_inf_izq_path = save_upload_file(
        logo_inf_izq,
        input_dir / "logo_inf_izq.png",
    )

    logo_inf_der_path = save_upload_file(
        logo_inf_der,
        input_dir / "logo_inf_der.png",
    )

    project_data = {
        "titulo": titulo,
        "info_extra": info_extra,
        "introduccion": introduccion,
        "imagen_portada": portada_path,

        "logo_sup_izq": logo_sup_izq_path,
        "logo_sup_der": logo_sup_der_path,
        "logo_inf_izq": logo_inf_izq_path,
        "logo_inf_der": logo_inf_der_path,
    }

    request = ReportGenerationRequest(
        job_id=job_id,
        zip_path=zip_path,
        output_dir=output_dir,
        temp_dir=temp_dir,
        project_data=project_data,
        usa_ubicacion=usa_ubicacion,
    )

    try:
        result = generate_report(request)

        return {
            "job_id": job_id,
            "status": "completed",
            "download_url": f"/reports/{job_id}/download",
            "zip_path": str(result.final_zip_path),
        }

    except Exception as exc:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Error generando reporte: {exc}",
        )


@router.post("/jobs", status_code=202)
async def create_report_job(
    background_tasks: BackgroundTasks,
    titulo: str = Form(...),
    info_extra: str = Form(""),
    introduccion: str = Form(""),
    usa_ubicacion: bool = Form(True),
    imagen_portada: UploadFile | None = File(None),
    logo_sup_izq: UploadFile | None = File(None),
    logo_sup_der: UploadFile | None = File(None),
    logo_inf_izq: UploadFile | None = File(None),
    logo_inf_der: UploadFile | None = File(None),
    evidencias_zip: UploadFile = File(...),
):
    if not evidencias_zip.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="El archivo de evidencias debe ser un ZIP.",
        )

    job_id = storage.create_job_id()
    dirs = storage.prepare_job_dirs(job_id)

    input_dir: Path = dirs["input_dir"]
    temp_dir: Path = dirs["temp_dir"]
    output_dir: Path = dirs["output_dir"]

    zip_path = input_dir / "evidencias.zip"

    save_limited_upload_file(evidencias_zip, zip_path)

    portada_path = save_upload_file(
        imagen_portada,
        input_dir / "portada.png",
    )

    logo_sup_izq_path = save_upload_file(
        logo_sup_izq,
        input_dir / "logo_sup_izq.png",
    )

    logo_sup_der_path = save_upload_file(
        logo_sup_der,
        input_dir / "logo_sup_der.png",
    )

    logo_inf_izq_path = save_upload_file(
        logo_inf_izq,
        input_dir / "logo_inf_izq.png",
    )

    logo_inf_der_path = save_upload_file(
        logo_inf_der,
        input_dir / "logo_inf_der.png",
    )

    project_data = build_project_data(
        titulo=titulo,
        info_extra=info_extra,
        introduccion=introduccion,
        portada_path=portada_path,
        logo_sup_izq_path=logo_sup_izq_path,
        logo_sup_der_path=logo_sup_der_path,
        logo_inf_izq_path=logo_inf_izq_path,
        logo_inf_der_path=logo_inf_der_path,
    )

    create_job_status(
        reports_status_dir(),
        job_id,
        message="Archivos recibidos. El reporte está en espera de iniciar.",
    )

    background_tasks.add_task(
        _run_report_job,
        job_id=job_id,
        zip_path=zip_path,
        output_dir=output_dir,
        temp_dir=temp_dir,
        project_data=project_data,
        usa_ubicacion=usa_ubicacion,
    )

    return {
        "job_id": job_id,
        "status": "queued",
        "status_url": f"/reports/{job_id}/status",
        "download_url": f"/reports/{job_id}/download",
    }


@router.get("/{job_id}/status")
async def get_report_job_status(job_id: str):
    normalized_job_id = normalize_job_id(job_id)
    payload = read_job_status(reports_status_dir(), normalized_job_id)

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


@router.get("/{job_id}/download")
def download_report(job_id: str):
    normalized_job_id = normalize_job_id(job_id)
    status_payload = read_job_status(reports_status_dir(), normalized_job_id)

    if status_payload is not None:
        if status_payload.get("status") == "failed":
            raise HTTPException(
                status_code=409,
                detail=(
                    status_payload.get("error")
                    or "La generación del reporte terminó con error."
                ),
            )

        if status_payload.get("status") != "completed":
            raise HTTPException(
                status_code=409,
                detail="El reporte todavía se está generando.",
            )

    job_dir = storage.get_job_dir(normalized_job_id)
    zip_path = job_dir / "output" / "Memoria_Tecnica_Final.zip"

    if not zip_path.exists():
        raise HTTPException(
            status_code=404,
            detail="El ZIP final no existe o aún no ha sido generado.",
        )

    return FileResponse(
        path=zip_path,
        filename="Memoria_Tecnica_Final.zip",
        media_type="application/zip",
    )

