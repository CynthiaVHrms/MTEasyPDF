import shutil
import traceback
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse

from app.services.storage_service import StorageService
from app.pdf_engine.generator import generate_report
from app.pdf_engine.models import ReportGenerationRequest


router = APIRouter(prefix="/reports", tags=["Reports"])

storage = StorageService()


@router.post("/generate")
async def generate_report_endpoint(
    titulo: str = Form(...),
    info_extra: str = Form(""),
    introduccion: str = Form(""),
    usa_ubicacion: bool = Form(True),
    imagen_portada: UploadFile | None = File(None),
    logo1: UploadFile | None = File(None),
    logo2: UploadFile | None = File(None),
    logo3: UploadFile | None = File(None),
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

    with open(zip_path, "wb") as buffer:
        shutil.copyfileobj(evidencias_zip.file, buffer)

    portada_path = None

    if imagen_portada and imagen_portada.filename:
        portada_path = input_dir / "portada.png"

        with open(portada_path, "wb") as buffer:
            shutil.copyfileobj(imagen_portada.file, buffer)

    logo_paths = []

    for index, logo in enumerate([logo1, logo2, logo3], start=1):
        if logo and logo.filename:
            logo_path = input_dir / f"logo_{index}.png"

            with open(logo_path, "wb") as buffer:
                shutil.copyfileobj(logo.file, buffer)

            logo_paths.append(str(logo_path))

    project_data = {
        "titulo": titulo,
        "info_extra": info_extra,
        "introduccion": introduccion,
        "imagen_portada": str(portada_path) if portada_path else "",
        "logos": logo_paths,
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


@router.get("/{job_id}/download")
def download_report(job_id: str):
    job_dir = storage.get_job_dir(job_id)
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