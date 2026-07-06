import datetime
import os
import re
import shutil
import unicodedata
import zipfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pandas as pd
from PIL import Image
from docx import Document
from docx.shared import Mm
from docxcompose.composer import Composer
from docxtpl import DocxTemplate, InlineImage


IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"]


@dataclass
class ProtocolDocumentResult:
    job_id: str
    output_docx_path: Path
    total_sitios: int
    total_documentos_generados: int


def normalizar_texto(texto):
    if pd.isna(texto):
        return ""

    texto = str(texto)
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = texto.lower()
    texto = texto.replace("-", " ").replace("_", " ")
    texto = re.sub(r"[^a-z0-9 ]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    return texto


def limpiar_prefijo_numerico(nombre_carpeta):
    return re.sub(r"^\d+\.\s+", "", str(nombre_carpeta))


def buscar_carpeta_flexible(ruta_padre, nombre_buscado):
    if not ruta_padre or not os.path.exists(ruta_padre):
        return None

    nombre_buscado_limpio = limpiar_prefijo_numerico(nombre_buscado)
    nombre_buscado_norm = normalizar_texto(nombre_buscado_limpio)

    for carpeta in os.listdir(ruta_padre):
        ruta_completa = os.path.join(ruta_padre, carpeta)

        if not os.path.isdir(ruta_completa):
            continue

        carpeta_limpia = limpiar_prefijo_numerico(carpeta)

        if normalizar_texto(carpeta_limpia) == nombre_buscado_norm:
            return ruta_completa

    return None


def safe_extract_zip(zip_path: Path, extract_dir: Path) -> None:
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            member_path = extract_dir / member.filename
            resolved_path = member_path.resolve()

            if not str(resolved_path).startswith(str(extract_dir.resolve())):
                raise ValueError("El ZIP contiene rutas no permitidas.")

            zip_ref.extract(member, extract_dir)


def find_evidence_root(extract_dir: Path) -> Path:
    candidates = []

    for path in extract_dir.rglob("*"):
        if path.is_dir() and "evidencia" in normalizar_texto(path.name):
            candidates.append(path)

    if candidates:
        return candidates[0]

    children = [p for p in extract_dir.iterdir() if p.is_dir()]

    if len(children) == 1:
        return children[0]

    return extract_dir


def format_excel_date(value):
    if isinstance(value, (pd.Timestamp, datetime.date)):
        return value.strftime("%d/%m/%Y")

    if pd.isna(value):
        return ""

    return str(value)


def build_inline_image(template: DocxTemplate, image_path: str):
    vertical_size = 7
    horizontal_size = 5.25

    try:
        with Image.open(image_path) as img:
            ancho_px, alto_px = img.size

        if ancho_px >= alto_px:
            return InlineImage(template, image_path, width=Mm(vertical_size * 10))

        return InlineImage(template, image_path, height=Mm(horizontal_size * 10))

    except Exception:
        return InlineImage(template, image_path, width=Mm(52.5))


def generate_protocol_document(
    excel_path: Path,
    evidence_zip_path: Path,
    template_docx_path: Path,
    work_dir: Path,
) -> ProtocolDocumentResult:
    if not excel_path.exists():
        raise FileNotFoundError(f"No existe el Excel: {excel_path}")

    if not evidence_zip_path.exists():
        raise FileNotFoundError(f"No existe el ZIP de evidencias: {evidence_zip_path}")

    if not template_docx_path.exists():
        raise FileNotFoundError(f"No existe la plantilla Word: {template_docx_path}")

    job_id = uuid4().hex

    job_dir = work_dir / job_id
    extract_dir = job_dir / "evidencias_extraidas"
    temp_dir = job_dir / "temp_docs"
    output_dir = job_dir / "output"

    output_docx_path = output_dir / "Protocolo_C5_Generado.docx"

    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)

    extract_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_extract_zip(evidence_zip_path, extract_dir)
    ruta_evidencias = find_evidence_root(extract_dir)

    hoja1 = pd.read_excel(excel_path, sheet_name=0)
    hoja2 = pd.read_excel(excel_path, sheet_name=1)

    hoja1.columns = hoja1.columns.str.strip()
    hoja2.columns = hoja2.columns.str.strip()

    required_hoja1 = ["ID", "Sitio"]
    required_hoja2 = ["ID", "Sitio", "clasificacion", "Foto"]

    missing_hoja1 = [col for col in required_hoja1 if col not in hoja1.columns]
    missing_hoja2 = [col for col in required_hoja2 if col not in hoja2.columns]

    if missing_hoja1:
        raise ValueError(
            "La Hoja 1 no contiene las columnas requeridas: "
            + ", ".join(missing_hoja1)
        )

    if missing_hoja2:
        raise ValueError(
            "La Hoja 2 no contiene las columnas requeridas: "
            + ", ".join(missing_hoja2)
        )

    hoja1["ID"] = hoja1["ID"].astype(str).str.strip()
    hoja2["ID"] = hoja2["ID"].astype(str).str.strip()

    archivos_generados = []
    total_sitios = len(hoja1)

    if total_sitios == 0:
        raise ValueError("La Hoja 1 del Excel no contiene registros.")

    for idx, fila_sitio in hoja1.iterrows():
        id_sitio = str(fila_sitio["ID"]).strip()
        nombre_sitio_real = str(fila_sitio["Sitio"]).strip()
        nombre_enlace = str(fila_sitio.get("Enlace", "")).strip()
        tipo_sitio_original = str(fila_sitio.get("TipoDeSitio", "")).strip().upper()

        if "LOCAL" in tipo_sitio_original:
            tipo_sitio_formateado = "Sitio Local"
        else:
            tipo_sitio_formateado = "Sitio Remoto"

        template = DocxTemplate(str(template_docx_path))

        registros_fotos = hoja2[
            (hoja2["ID"] == id_sitio)
            & (hoja2["Sitio"].astype(str).str.strip() == nombre_sitio_real)
        ]

        clasificaciones_unicas = (
            registros_fotos["clasificacion"]
            .fillna("SIN CLASIFICACION")
            .astype(str)
            .str.strip()
            .unique()
        )

        lista_clasificaciones = []

        ruta_enlace_folder = buscar_carpeta_flexible(str(ruta_evidencias), nombre_enlace)
        ruta_sitio_folder = buscar_carpeta_flexible(ruta_enlace_folder, nombre_sitio_real)

        for clasificacion in clasificaciones_unicas:
            fotos_clase = registros_fotos[
                registros_fotos["clasificacion"]
                .fillna("SIN CLASIFICACION")
                .astype(str)
                .str.strip()
                == clasificacion
            ]

            ruta_clasificacion = buscar_carpeta_flexible(
                ruta_sitio_folder,
                clasificacion,
            )

            lista_individual = []

            for _, fila_foto in fotos_clase.iterrows():
                nombre_evidencia = str(fila_foto.get("Foto", "")).strip()

                val_nombre_doc = fila_foto.get("NombreDeImagenEnDocumento")

                if (
                    pd.isna(val_nombre_doc)
                    or str(val_nombre_doc).strip().lower() == "nan"
                    or str(val_nombre_doc).strip() == ""
                ):
                    nombre_documento = " "
                else:
                    nombre_documento = str(val_nombre_doc).strip()

                datos_bloque = {
                    "nombre_foto": nombre_documento,
                    "tipo_equipo": str(fila_foto.get("TipoDeEquipo", "")),
                    "sitio": nombre_sitio_real,
                    "imagen": "",
                }

                ruta_imagen = None

                if ruta_clasificacion:
                    for ext in IMAGE_EXTENSIONS:
                        posible = os.path.join(
                            ruta_clasificacion,
                            f"{nombre_evidencia}{ext}",
                        )

                        if os.path.exists(posible):
                            ruta_imagen = posible
                            break

                if ruta_imagen:
                    datos_bloque["imagen"] = build_inline_image(
                        template,
                        ruta_imagen,
                    )
                else:
                    datos_bloque["imagen"] = f"[No encontrada: {nombre_evidencia}]"

                lista_individual.append(datos_bloque)

            lista_pares = []

            for i in range(0, len(lista_individual), 2):
                par = {
                    "izq": lista_individual[i],
                    "der": lista_individual[i + 1]
                    if (i + 1) < len(lista_individual)
                    else None,
                }

                lista_pares.append(par)

            lista_clasificaciones.append(
                {
                    "clasificacion": clasificacion,
                    "pares": lista_pares,
                }
            )

        fecha_arribo = format_excel_date(fila_sitio.get("FechaDeArribo", ""))
        fecha_term = format_excel_date(fila_sitio.get("FechaDeTerminación", ""))

        datos_render = {
            "ID": id_sitio,
            "Enlace": nombre_enlace,
            "Sitio": nombre_sitio_real,
            "NoTicket": str(fila_sitio.get("NoTicket", "")),
            "TipoDeSitio": tipo_sitio_formateado,
            "TipoDeEquipo": str(fila_sitio.get("TipoDeEquipo", "")),
            "Dato1": fecha_arribo,
            "Dato2": str(fila_sitio.get("HoraDeArribo", "")),
            "Dato3": fecha_term,
            "Dato4": str(fila_sitio.get("HoraDeTerminación", "")),
            "clasificaciones": lista_clasificaciones,
        }

        template.render(datos_render)

        temporal_path = temp_dir / f"temp_sitio_{id_sitio}_{idx}.docx"
        template.save(str(temporal_path))

        archivos_generados.append(temporal_path)

    if not archivos_generados:
        raise ValueError("No se generaron documentos.")

    documento_base = Document(str(archivos_generados[0]))
    composer = Composer(documento_base)

    for archivo in archivos_generados[1:]:
        documento_base.add_page_break()
        doc_temp = Document(str(archivo))
        composer.append(doc_temp)

    composer.save(str(output_docx_path))

    return ProtocolDocumentResult(
        job_id=job_id,
        output_docx_path=output_docx_path,
        total_sitios=total_sitios,
        total_documentos_generados=len(archivos_generados),
    )