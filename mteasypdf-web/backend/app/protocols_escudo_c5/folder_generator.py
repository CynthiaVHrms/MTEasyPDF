import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pandas as pd


REQUIRED_COLUMNS = ["Enlace", "Sitio", "clasificacion"]


@dataclass
class FolderGenerationResult:
    job_id: str
    output_dir: Path
    zip_path: Path
    total_enlaces: int
    total_sitios: int
    total_clasificaciones: int


def clean_folder_name(value: str) -> str:
    value = str(value).strip()

    invalid_chars = r'[<>:"/\\|?*]'
    value = re.sub(invalid_chars, "_", value)

    value = re.sub(r"\s+", " ", value)
    value = value.strip(" .")

    if not value or value.lower() == "nan":
        return "SIN_NOMBRE"

    return value


def create_zip_from_directory(source_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(
        zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=4,
    ) as zipf:
        for path in source_dir.rglob("*"):
            relative_path = path.relative_to(source_dir)

            if path.is_dir():
                zipf.writestr(str(relative_path).replace("\\", "/") + "/", "")
            else:
                zipf.write(path, relative_path)


def generate_folders_from_excel(
    excel_path: Path,
    work_dir: Path,
    sheet_name: str = "Hoja2",
) -> FolderGenerationResult:
    if not excel_path.exists():
        raise FileNotFoundError(f"No existe el archivo Excel: {excel_path}")

    job_id = uuid4().hex

    job_dir = work_dir / job_id
    output_dir = job_dir / "output" / "Estructura_C5"
    zip_path = job_dir / "output" / "Estructura_Carpetas_C5.zip"

    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        df = pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as exc:
        raise ValueError(
            f"No se pudo leer la hoja '{sheet_name}' del archivo Excel. "
            f"Verifica que el archivo tenga esa hoja."
        ) from exc

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing_columns:
        raise ValueError(
            "El Excel no contiene las columnas requeridas: "
            + ", ".join(missing_columns)
            + ". Columnas obligatorias: Enlace, Sitio, clasificacion."
        )

    df = df[REQUIRED_COLUMNS].copy()

    df["Enlace"] = df["Enlace"].astype(str).str.strip()
    df["Sitio"] = df["Sitio"].astype(str).str.strip()
    df["clasificacion"] = df["clasificacion"].astype(str).str.strip()

    df = df[
        (df["Enlace"].str.lower() != "nan")
        & (df["Sitio"].str.lower() != "nan")
        & (df["clasificacion"].str.lower() != "nan")
    ]

    total_enlaces = 0
    total_sitios = 0
    total_clasificaciones = 0

    enlaces_unicos = df["Enlace"].dropna().unique()

    for idx_enlace, enlace in enumerate(enlaces_unicos, start=1):
        df_enlace = df[df["Enlace"] == enlace]

        enlace_limpio = clean_folder_name(enlace)
        enlace_dir = output_dir / f"{idx_enlace}. {enlace_limpio}"
        enlace_dir.mkdir(parents=True, exist_ok=True)
        total_enlaces += 1

        sitios_unicos = df_enlace["Sitio"].dropna().unique()

        for idx_sitio, sitio in enumerate(sitios_unicos, start=1):
            df_sitio = df_enlace[df_enlace["Sitio"] == sitio]

            sitio_limpio = clean_folder_name(sitio)
            sitio_dir = enlace_dir / f"{idx_sitio}. {sitio_limpio}"
            sitio_dir.mkdir(parents=True, exist_ok=True)
            total_sitios += 1

            clasificaciones = df_sitio["clasificacion"]
            clasificaciones_filtradas = clasificaciones[
                clasificaciones != clasificaciones.shift()
            ].tolist()

            for idx_clas, clasificacion in enumerate(
                clasificaciones_filtradas,
                start=1,
            ):
                clasificacion_limpia = clean_folder_name(clasificacion)

                if clasificacion_limpia == "SIN_NOMBRE":
                    continue

                clasificacion_dir = (
                    sitio_dir / f"{idx_clas}. {clasificacion_limpia}"
                )
                clasificacion_dir.mkdir(parents=True, exist_ok=True)
                total_clasificaciones += 1

    create_zip_from_directory(output_dir, zip_path)

    return FolderGenerationResult(
        job_id=job_id,
        output_dir=output_dir,
        zip_path=zip_path,
        total_enlaces=total_enlaces,
        total_sitios=total_sitios,
        total_clasificaciones=total_clasificaciones,
    )