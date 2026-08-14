from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


router = APIRouter(
    prefix="/protocols/templates",
    tags=["protocol-templates"],
)


TEMPLATE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "templates"
)
ASSETS_ROOT = Path(__file__).resolve().parents[2] / "assets"
MANUAL_FILENAME = "Manual_Usuario_MIA_v2.1.0.pdf"
MANUAL_PATH = ASSETS_ROOT / MANUAL_FILENAME

XLSX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument."
    "spreadsheetml.sheet"
)
PDF_MEDIA_TYPE = "application/pdf"


@dataclass(frozen=True)
class TemplateSpec:
    template_id: str
    internal_filename: str
    download_filename: str
    version: str
    description: str

    @property
    def path(self) -> Path:
        return TEMPLATE_ROOT / self.internal_filename


TEMPLATES: dict[str, TemplateSpec] = {
    "c5-sites-v1": TemplateSpec(
        template_id="c5-sites-v1",
        internal_filename="c5-informacion-sitios-v1.xlsx",
        download_filename=(
            "C5_Información_de_los_sitios_versión_1_0.xlsx"
        ),
        version="1.0",
        description=(
            "Plantilla oficial para crear la estructura y generar "
            "un protocolo C5 nuevo."
        ),
    ),
    "c5-tags-v1": TemplateSpec(
        template_id="c5-tags-v1",
        internal_filename="c5-etiquetas-word-v1.xlsx",
        download_filename="C5_Etiquetas_Word_v1.xlsx",
        version="1.0",
        description=(
            "Plantilla oficial para completar un Word existente "
            "mediante etiquetas."
        ),
    ),
}


def _get_template(template_id: str) -> TemplateSpec:
    template = TEMPLATES.get(template_id)

    if template is None:
        raise HTTPException(
            status_code=404,
            detail="La plantilla solicitada no existe.",
        )

    if not template.path.is_file():
        raise HTTPException(
            status_code=503,
            detail=(
                "La plantilla está registrada en el sistema, pero el "
                "archivo no está disponible en esta instalación. "
                "Verifica el despliegue del backend."
            ),
        )

    return template


@router.get("")
def list_templates() -> dict[str, object]:
    """
    Catálogo estable de plantillas disponibles.

    El frontend utiliza identificadores internos simples en lugar de
    construir rutas a partir de nombres físicos de archivos.
    """

    return {
        "templates": [
            {
                "id": template.template_id,
                "version": template.version,
                "description": template.description,
                "available": template.path.is_file(),
            }
            for template in TEMPLATES.values()
        ]
    }


@router.get("/manual/download", response_class=FileResponse)
def download_user_manual() -> FileResponse:
    """
    Descarga del manual oficial de usuario de MIA.
    """

    if not MANUAL_PATH.is_file():
        raise HTTPException(
            status_code=503,
            detail=(
                "El manual de usuario no está disponible en esta "
                "instalación. Verifica el despliegue del backend."
            ),
        )

    return FileResponse(
        path=MANUAL_PATH,
        filename=MANUAL_FILENAME,
        media_type=PDF_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-store",
        },
    )


@router.get("/{template_id}/download", response_class=FileResponse)
def download_template(template_id: str) -> FileResponse:
    """
    Descarga una plantilla oficial usando un identificador estable.

    La ruta física del archivo nunca se recibe desde el navegador y no se
    expone al usuario. Esto evita dependencias con nombres que contienen
    espacios, acentos o rutas del sistema operativo.
    """

    template = _get_template(template_id)

    return FileResponse(
        path=template.path,
        filename=template.download_filename,
        media_type=XLSX_MEDIA_TYPE,
        headers={
            "Cache-Control": "no-store",
            "X-Template-Id": template.template_id,
            "X-Template-Version": template.version,
        },
    )