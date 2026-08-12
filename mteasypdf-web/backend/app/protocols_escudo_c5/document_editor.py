from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import unicodedata
import zipfile

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pandas as pd

from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

from docx import Document
from docx.document import Document as DocumentObject
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from docx.table import Table, _Cell
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.text.paragraph import Paragraph


ImageFile.LOAD_TRUNCATED_IMAGES = True

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
    ".jfif",
}

TAG_MANIFEST_FILENAME = "manifest_word_tags.json"
TAG_STRUCTURE_ZIP_FILENAME = "Estructura_Etiquetas_Word.zip"
TAGGED_OUTPUT_DOCX_FILENAME = "Documento_Completo_Etiquetas.docx"
MAX_IMAGES_PER_PAGE = 4


@dataclass
class TagEvidenceRow:
    tag_key: str
    tag_display: str
    section: str
    subsection: str
    # ``evidence`` se conserva como nombre interno por compatibilidad con
    # diagnósticos existentes, pero su valor ahora proviene exclusivamente
    # de la columna ``Orden`` del Excel.
    evidence: str

    # ``title`` se conserva como nombre interno; el encabezado oficial del
    # Excel ahora es ``NombreDeFoto``.
    title: str

    # Campo heredado. Ya no forma parte del Excel definitivo ni se imprime
    # en el Word, pero se acepta si un archivo antiguo todavía lo contiene.
    description: str

    # Metadatos operativos que se muestran debajo de cada fotografía.
    arrival_date: str
    arrival_time: str
    completion_date: str
    completion_time: str
    location: str
    ticket: str

    order: int


@dataclass
class TagGroup:
    tag_key: str
    tag_display: str
    section: str
    subsection: str
    evidences: list[TagEvidenceRow]


@dataclass
class TaggedFoldersResult:
    job_id: str
    zip_path: Path
    manifest_path: Path
    total_tags: int
    total_evidences: int


@dataclass
class TaggedDocumentResult:
    job_id: str
    output_docx_path: Path
    diagnostics_path: Path
    total_tags: int
    total_tags_replaced: int
    total_tags_not_found: int
    total_images_inserted: int
    total_images_missing: int
    total_images_omitted: int


class InvalidTaggedImageError(ValueError):
    """Error controlado para imágenes que no se pueden insertar en Word."""


class InvalidTaggedExcelError(ValueError):
    """Error controlado para Excel de etiquetas inválido."""


def normalizar_texto(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value)
    text = "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
    text = text.lower()
    text = text.replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9 ]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_text(value: object) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    return text


def format_document_date(value: object) -> str:
    """
    Convierte fechas provenientes de Excel al formato dd/mm/aaaa utilizado
    en los Protocolos C5. Acepta fechas reales de Excel, datetime y texto.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    if isinstance(value, pd.Timestamp):
        return value.strftime("%d/%m/%Y")

    if isinstance(value, dt.datetime):
        return value.strftime("%d/%m/%Y")

    if isinstance(value, dt.date):
        return value.strftime("%d/%m/%Y")

    text = clean_text(value)
    if not text:
        return ""

    try:
        parsed = pd.to_datetime(
            text,
            dayfirst=True,
            errors="coerce",
        )
        if not pd.isna(parsed):
            return parsed.strftime("%d/%m/%Y")
    except (TypeError, ValueError, OverflowError):
        pass

    return text


def format_document_time(value: object) -> str:
    """
    Normaliza horas provenientes de Excel sin obligar al usuario a utilizar
    un único formato. También soporta la fracción de día usada por Excel.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    if isinstance(value, pd.Timestamp):
        return value.strftime("%H:%M")

    if isinstance(value, dt.datetime):
        return value.strftime("%H:%M")

    if isinstance(value, dt.time):
        return value.strftime("%H:%M")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric_value = float(value)
        if 0 <= numeric_value < 1:
            total_seconds = round(numeric_value * 24 * 60 * 60)
            hours = (total_seconds // 3600) % 24
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            if seconds:
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            return f"{hours:02d}:{minutes:02d}"

    return clean_text(value)


def join_date_and_time(date_value: str, time_value: str) -> str:
    """Une fecha y hora respetando los casos donde uno de los dos falte."""

    date_value = clean_text(date_value)
    time_value = clean_text(time_value)

    if date_value and time_value:
        return f"{date_value} a las {time_value}"
    if date_value:
        return date_value
    if time_value:
        return time_value
    return ""


def safe_filename_fragment(value: object, fallback: str = "SIN_NOMBRE") -> str:
    text = clean_text(value) or fallback
    text = re.sub(r'[<>:"/\\|?*]', "_", text)
    text = re.sub(r"\s+", "_", text)
    text = text.strip(" ._")
    return text[:120] or fallback


def extract_tag_key(value: object) -> str:
    """
    Convierte una etiqueta escrita como {{TAG}}, [[TAG]], <<TAG>> o TAG
    en una clave interna estable: TAG.
    """

    text = clean_text(value)
    if not text:
        return ""

    wrappers = [
        ("{{", "}}"),
        ("[[", "]]"),
        ("<<", ">>"),
        ("${", "}"),
    ]

    changed = True
    while changed:
        changed = False
        for start, end in wrappers:
            if text.startswith(start) and text.endswith(end):
                text = text[len(start) : -len(end)].strip()
                changed = True

    text = re.sub(r"\s+", "_", text.strip())
    text = text.strip("{}[]<>")
    return text


def tag_variants(tag_key: str, tag_display: str | None = None) -> list[str]:
    """
    Devuelve las variantes de una etiqueta en orden seguro.

    Los marcadores completos se colocan antes que la clave desnuda para evitar
    que al reemplazar ``PENDIENTE_X`` dentro de ``{{PENDIENTE_X}}`` queden
    residuos como ``{{}}``.
    """

    clean_key = extract_tag_key(tag_key)
    variants: list[str] = []

    for candidate in [
        tag_display or "",
        f"{{{{{clean_key}}}}}",
        f"[[{clean_key}]]",
        f"<<{clean_key}>>",
        f"${{{clean_key}}}",
        clean_key,
    ]:
        candidate = clean_text(candidate)
        if candidate and candidate not in variants:
            variants.append(candidate)

    return variants


def remove_tag_marker_from_paragraph(
    paragraph: Paragraph,
    tag_key: str,
    tag_display: str | None = None,
) -> bool:
    """
    Elimina una etiqueta completa del párrafo, incluso cuando contiene espacios
    dentro de los delimitadores.

    También limpia residuos de versiones anteriores, por ejemplo ``{{}}``.
    Devuelve ``True`` cuando el párrafo queda vacío después de la limpieza.
    """

    original_text = paragraph.text or ""
    cleaned_text = original_text
    clean_key = extract_tag_key(tag_key)

    if clean_key:
        escaped_key = re.escape(clean_key)
        full_marker_patterns = [
            rf"\{{\{{\s*{escaped_key}\s*\}}\}}",
            rf"\[\[\s*{escaped_key}\s*\]\]",
            rf"<<\s*{escaped_key}\s*>>",
            rf"\$\{{\s*{escaped_key}\s*\}}",
        ]

        for pattern in full_marker_patterns:
            cleaned_text = re.sub(
                pattern,
                "",
                cleaned_text,
                flags=re.IGNORECASE,
            )

    display_value = clean_text(tag_display or "")
    if display_value:
        cleaned_text = re.sub(
            re.escape(display_value),
            "",
            cleaned_text,
            flags=re.IGNORECASE,
        )

    if clean_key:
        cleaned_text = re.sub(
            rf"(?<![A-Za-z0-9_]){re.escape(clean_key)}(?![A-Za-z0-9_])",
            "",
            cleaned_text,
            flags=re.IGNORECASE,
        )

    # Limpia delimitadores vacíos que pudieron quedar en documentos generados
    # con versiones anteriores del sistema.
    cleaned_text = re.sub(r"\{\{\s*\}\}", "", cleaned_text)
    cleaned_text = re.sub(r"\[\[\s*\]\]", "", cleaned_text)
    cleaned_text = re.sub(r"<<\s*>>", "", cleaned_text)
    cleaned_text = re.sub(r"\$\{\s*\}", "", cleaned_text)
    cleaned_text = re.sub(r"[ 	]+", " ", cleaned_text)
    cleaned_text = re.sub(r"\s*\n\s*", "\n", cleaned_text)
    cleaned_text = cleaned_text.strip()

    if cleaned_text != original_text:
        paragraph.text = cleaned_text

    return not cleaned_text


def find_column(columns: list[str], aliases: list[str], required_name: str) -> str:
    normalized = {normalizar_texto(column): column for column in columns}

    for alias in aliases:
        key = normalizar_texto(alias)
        if key in normalized:
            return normalized[key]

    raise InvalidTaggedExcelError(
        "El Excel de etiquetas no contiene la columna requerida: "
        f"{required_name}."
    )


def optional_column(columns: list[str], aliases: list[str]) -> str | None:
    normalized = {normalizar_texto(column): column for column in columns}

    for alias in aliases:
        key = normalizar_texto(alias)
        if key in normalized:
            return normalized[key]

    return None


def parse_order(value: object, default: int) -> int:
    if pd.isna(value):
        return default

    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def read_tag_groups_from_excel(excel_path: Path) -> list[TagGroup]:
    excel_path = Path(excel_path)

    if not excel_path.exists() or not excel_path.is_file():
        raise FileNotFoundError(f"No existe el Excel de etiquetas: {excel_path}")

    try:
        dataframe = pd.read_excel(excel_path, sheet_name=0)
    except Exception as exc:
        raise InvalidTaggedExcelError(
            "No fue posible leer el Excel de etiquetas. Verifica que sea un "
            "archivo .xlsx válido y que no esté dañado."
        ) from exc

    if dataframe.empty:
        raise InvalidTaggedExcelError("El Excel de etiquetas no contiene registros.")

    dataframe.columns = dataframe.columns.astype(str).str.strip()
    columns = list(dataframe.columns)

    tag_column = find_column(
        columns,
        ["Etiqueta", "Tag", "Marcador", "Etiqueta Word", "EtiquetaWord"],
        "Etiqueta",
    )
    section_column = find_column(
        columns,
        ["Seccion", "Sección", "Section", "Titulo Seccion", "Título Sección"],
        "Seccion",
    )
    # La plantilla definitiva usa una sola columna como fuente de verdad:
    # ``Orden`` identifica la fotografía (1, 2, 3, ...) y también define
    # su orden de aparición. La antigua columna ``Evidencia`` ya no se usa.
    order_column = find_column(
        columns,
        ["Orden", "No", "Número", "Numero", "Indice", "Índice"],
        "Orden",
    )

    subsection_column = optional_column(
        columns,
        ["Subseccion", "Subsección", "Subsection", "Subtitulo", "Subtítulo"],
    )
    title_column = optional_column(
        columns,
        [
            # Nombre oficial de la plantilla definitiva.
            "NombreDeFoto",
            "Nombre de foto",
            "NombreFoto",
            # Alias heredados para no romper Excels anteriores.
            "TituloEnDocumento",
            "TítuloEnDocumento",
            "Titulo en documento",
            "Título en documento",
            "NombreDeImagenEnDocumento",
            "Nombre en documento",
            "Titulo Evidencia",
            "Título Evidencia",
        ],
    )
    description_column = optional_column(
        columns,
        ["Descripcion", "Descripción", "Comentario", "Comentarios", "Observacion", "Observación"],
    )

    arrival_date_column = optional_column(
        columns,
        ["FechaDeArribo", "Fecha de arribo", "Fecha Arribo", "FechaArribo"],
    )
    arrival_time_column = optional_column(
        columns,
        ["HoraDeArribo", "Hora de arribo", "Hora Arribo", "HoraArribo"],
    )
    completion_date_column = optional_column(
        columns,
        [
            "FechaDeTerminación",
            "FechaDeTerminacion",
            "Fecha de terminación",
            "Fecha de terminacion",
            "FechaTerminacion",
        ],
    )
    completion_time_column = optional_column(
        columns,
        [
            "HoraDeTerminación",
            "HoraDeTerminacion",
            "Hora de terminación",
            "Hora de terminacion",
            "HoraTerminacion",
        ],
    )
    location_column = optional_column(
        columns,
        ["Lugar", "Ubicacion", "Ubicación", "Sitio"],
    )
    ticket_column = optional_column(
        columns,
        [
            "NoTicket",
            "No. De ticket",
            "No. de ticket",
            "NumeroTicket",
            "NúmeroTicket",
            "Ticket",
        ],
    )
    rows: list[TagEvidenceRow] = []

    for index, row in dataframe.iterrows():
        tag_display = clean_text(row.get(tag_column, ""))
        tag_key = extract_tag_key(tag_display)
        section = clean_text(row.get(section_column, ""))
        order_raw = row.get(order_column, "")
        order_text = clean_text(order_raw)

        if not tag_key and not section and not order_text:
            continue

        if not tag_key:
            raise InvalidTaggedExcelError(
                f"La fila {index + 2} no tiene etiqueta. Captura un valor como "
                "TAG_CONDICION_HERRAJES."
            )

        if not section:
            raise InvalidTaggedExcelError(
                f"La fila {index + 2} no tiene sección. Captura el título que "
                "se insertará en el Word."
            )

        if not order_text:
            raise InvalidTaggedExcelError(
                f"La fila {index + 2} no tiene Orden. Captura el número de la "
                "fotografía esperada, por ejemplo 1, 2 o 3."
            )

        try:
            order_number = int(float(order_text))
        except (TypeError, ValueError):
            raise InvalidTaggedExcelError(
                f"La fila {index + 2} tiene un Orden inválido: {order_text!r}. "
                "Utiliza números enteros positivos como 1, 2 o 3."
            )

        try:
            numeric_order = float(order_text)
        except (TypeError, ValueError):
            numeric_order = float(order_number)

        if order_number < 1 or numeric_order != order_number:
            raise InvalidTaggedExcelError(
                f"La fila {index + 2} tiene un Orden inválido: {order_text!r}. "
                "Utiliza números enteros positivos como 1, 2 o 3."
            )

        # Orden reemplaza por completo a la antigua columna Evidencia.
        # El valor se convierte a texto limpio para localizar archivos como
        # 1.jpg, 1.0.jpeg, 01.png, etc.
        evidence = str(order_number)

        rows.append(
            TagEvidenceRow(
                tag_key=tag_key,
                tag_display=tag_display or f"{{{{{tag_key}}}}}",
                section=section,
                subsection=clean_text(row.get(subsection_column, "")) if subsection_column else "",
                evidence=evidence,
                title=clean_text(row.get(title_column, "")) if title_column else "",
                description=clean_text(row.get(description_column, "")) if description_column else "",
                arrival_date=(
                    format_document_date(row.get(arrival_date_column, ""))
                    if arrival_date_column
                    else ""
                ),
                arrival_time=(
                    format_document_time(row.get(arrival_time_column, ""))
                    if arrival_time_column
                    else ""
                ),
                completion_date=(
                    format_document_date(row.get(completion_date_column, ""))
                    if completion_date_column
                    else ""
                ),
                completion_time=(
                    format_document_time(row.get(completion_time_column, ""))
                    if completion_time_column
                    else ""
                ),
                location=(
                    clean_text(row.get(location_column, ""))
                    if location_column
                    else ""
                ),
                ticket=(
                    clean_text(row.get(ticket_column, ""))
                    if ticket_column
                    else ""
                ),
                order=order_number,
            )
        )

    if not rows:
        raise InvalidTaggedExcelError("El Excel de etiquetas no contiene filas válidas.")

    # Como Orden ahora identifica la fotografía y define su posición, no puede
    # repetirse dentro de una misma etiqueta: dos archivos con el mismo Orden
    # serían ambiguos.
    seen_orders: dict[tuple[str, int], int] = {}
    for item_index, item in enumerate(rows, start=2):
        key = (item.tag_key, item.order)
        if key in seen_orders:
            first_row = seen_orders[key]
            raise InvalidTaggedExcelError(
                f"La etiqueta {item.tag_key!r} tiene el Orden {item.order} repetido "
                f"(filas {first_row} y {item_index}). Cada Orden debe ser único "
                "dentro de la misma etiqueta."
            )
        seen_orders[key] = item_index

    grouped: dict[str, TagGroup] = {}

    # Conserva el orden en el que las etiquetas aparecen por primera vez en el
    # Excel; dentro de cada etiqueta, ``Orden`` controla las fotografías.
    for item in rows:
        if item.tag_key not in grouped:
            grouped[item.tag_key] = TagGroup(
                tag_key=item.tag_key,
                tag_display=item.tag_display,
                section=item.section,
                subsection=item.subsection,
                evidences=[],
            )

        grouped[item.tag_key].evidences.append(item)

    for group in grouped.values():
        group.evidences.sort(key=lambda entry: entry.order)

    return list(grouped.values())


def safe_extract_zip(zip_path: Path, extract_dir: Path) -> None:
    zip_path = Path(zip_path)
    extract_dir = Path(extract_dir)

    if not zip_path.exists() or not zip_path.is_file():
        raise FileNotFoundError(f"No existe el ZIP de evidencias: {zip_path}")

    if not zipfile.is_zipfile(zip_path):
        raise ValueError("El archivo de evidencias no es un ZIP válido.")

    extract_dir.mkdir(parents=True, exist_ok=True)
    extract_root = extract_dir.resolve()

    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            if member.flag_bits & 0x1:
                raise ValueError("El ZIP contiene archivos protegidos con contraseña.")

            member_name = member.filename.replace("\\", "/")
            if member_name.startswith("/") or ".." in Path(member_name).parts:
                raise ValueError("El ZIP contiene rutas no permitidas.")

            destination = (extract_dir / member_name).resolve()
            try:
                destination.relative_to(extract_root)
            except ValueError as exc:
                raise ValueError("El ZIP contiene rutas fuera de la carpeta de trabajo.") from exc

        zip_ref.extractall(extract_dir)


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_tag_manifest(groups: list[TagGroup]) -> dict[str, object]:
    return {
        "schema_version": "2.0",
        "created_at": dt.datetime.now().isoformat(timespec="seconds"),
        "description": "Estructura generada para completar un Word mediante etiquetas reemplazables.",
        "tags": [
            {
                "tag_key": group.tag_key,
                "tag_tokens": tag_variants(group.tag_key, group.tag_display),
                "section": group.section,
                "subsection": group.subsection,
                "folder_name": folder_name_for_group(position, group),
                "evidences": [
                    {
                        "orden": evidence.order,
                        "nombre_de_foto": evidence.title,
                        # Alias internos para compatibilidad con diagnósticos y
                        # ZIP generados por versiones anteriores.
                        "evidence": evidence.evidence,
                        "title": evidence.title,
                        "fecha_arribo": evidence.arrival_date,
                        "hora_arribo": evidence.arrival_time,
                        "fecha_terminacion": evidence.completion_date,
                        "hora_terminacion": evidence.completion_time,
                        "lugar": evidence.location,
                        "no_ticket": evidence.ticket,
                    }
                    for evidence in group.evidences
                ],
            }
            for position, group in enumerate(groups, start=1)
        ],
    }


def folder_name_for_group(position: int, group: TagGroup) -> str:
    section = safe_filename_fragment(group.section, "SECCION")
    subsection = safe_filename_fragment(group.subsection, "GENERAL") if group.subsection else "GENERAL"
    tag_key = safe_filename_fragment(group.tag_key, "TAG")
    return f"{position:02d}. {tag_key} - {section} - {subsection}"


def generate_tagged_document_folders(
    excel_path: Path,
    work_dir: Path,
) -> TaggedFoldersResult:
    groups = read_tag_groups_from_excel(Path(excel_path))
    job_id = uuid4().hex
    job_dir = Path(work_dir) / job_id
    structure_dir = job_dir / "estructura"
    output_dir = job_dir / "output"
    root_dir = structure_dir / "Estructura_Etiquetas_Word"

    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)

    root_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = build_tag_manifest(groups)
    manifest_path = root_dir / TAG_MANIFEST_FILENAME
    write_text_file(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))

    total_evidences = 0

    for position, group in enumerate(groups, start=1):
        folder_name = folder_name_for_group(position, group)
        tag_dir = root_dir / folder_name
        tag_dir.mkdir(parents=True, exist_ok=True)
        total_evidences += len(group.evidences)

        expected_lines = [
            "COLOCA AQUÍ LAS EVIDENCIAS DE ESTA ETIQUETA",
            "",
            f"Etiqueta en Word: {{{{{group.tag_key}}}}}",
            f"Sección: {group.section}",
            f"Subsección: {group.subsection or 'General'}",
            "",
            "Fotografías esperadas (según la columna Orden):",
        ]

        for evidence in group.evidences:
            expected_lines.append(
                f"- Orden {evidence.order}"
                + (f" | {evidence.title}" if evidence.title else "")
            )

        expected_lines.extend(
            [
                "",
                "Notas:",
                "- El nombre del archivo se toma de Orden. Ejemplo: Orden 1 puede ser 1.jpg, 1.0.jpeg o 01.png.",
                "- No elimines este archivo si quieres conservar la guía visual de la carpeta.",
            ]
        )

        write_text_file(tag_dir / "_COLOCAR_EVIDENCIAS_AQUI.txt", "\n".join(expected_lines))

    zip_path = output_dir / TAG_STRUCTURE_ZIP_FILENAME

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
        for path in root_dir.rglob("*"):
            zip_file.write(path, path.relative_to(structure_dir))

    return TaggedFoldersResult(
        job_id=job_id,
        zip_path=zip_path,
        manifest_path=manifest_path,
        total_tags=len(groups),
        total_evidences=total_evidences,
    )


def load_manifest(extract_dir: Path) -> dict[str, object] | None:
    manifests = list(extract_dir.rglob(TAG_MANIFEST_FILENAME))
    if not manifests:
        return None

    try:
        return json.loads(manifests[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def find_group_folder(
    extract_dir: Path,
    group: TagGroup,
    manifest: dict[str, object] | None,
) -> Path | None:
    if manifest:
        for item in manifest.get("tags", []):
            if not isinstance(item, dict):
                continue

            if item.get("tag_key") != group.tag_key:
                continue

            folder_name = clean_text(item.get("folder_name", ""))
            if folder_name:
                matches = [path for path in extract_dir.rglob(folder_name) if path.is_dir()]
                if matches:
                    return matches[0]

    tag_key_normalized = normalizar_texto(group.tag_key)
    section_normalized = normalizar_texto(group.section)
    candidates = [path for path in extract_dir.rglob("*") if path.is_dir()]

    exact_candidates = [
        path
        for path in candidates
        if tag_key_normalized and tag_key_normalized in normalizar_texto(path.name)
    ]

    if exact_candidates:
        exact_candidates.sort(key=lambda item: len(item.parts))
        return exact_candidates[0]

    section_candidates = [
        path
        for path in candidates
        if section_normalized and section_normalized in normalizar_texto(path.name)
    ]

    if len(section_candidates) == 1:
        return section_candidates[0]

    return None


def split_known_image_extension(name: str) -> tuple[str, str]:
    path = Path(name)
    suffix = path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return path.stem, suffix
    return name, ""


def evidence_tokens(value: str) -> set[str]:
    base, _ = split_known_image_extension(clean_text(value))
    normalized = normalizar_texto(base)
    tokens = {normalized} if normalized else set()

    numeric_match = re.match(r"^(\d+)(?:\.0+)?$", base.strip())
    if numeric_match:
        number = int(numeric_match.group(1))
        tokens.add(str(number))
        tokens.add(f"{number:02d}")
        tokens.add(f"{number:03d}")
        tokens.add(f"{number} 0")

    return {token for token in tokens if token}


def image_matches_evidence(image_path: Path, evidence_name: str) -> bool:
    if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
        return False

    expected = evidence_tokens(evidence_name)
    if not expected:
        return False

    image_base, _ = split_known_image_extension(image_path.name)
    image_normalized = normalizar_texto(image_base)

    if image_normalized in expected:
        return True

    image_parts = set(image_normalized.split())
    return bool(expected.intersection(image_parts))


def find_evidence_image(group_folder: Path | None, evidence_name: str) -> Path | None:
    if not group_folder or not group_folder.exists() or not group_folder.is_dir():
        return None

    image_files = [
        path
        for path in group_folder.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    exact_name = clean_text(evidence_name).casefold()
    for path in image_files:
        if path.name.casefold() == exact_name:
            return path

    matches = [path for path in image_files if image_matches_evidence(path, evidence_name)]

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        matches.sort(key=lambda item: (len(item.parts), item.name.casefold()))
        return matches[0]

    return None


def normalize_image_for_docx(source_path: Path, normalized_images_dir: Path) -> Path:
    source_path = Path(source_path)
    normalized_images_dir = Path(normalized_images_dir)

    if not source_path.exists() or not source_path.is_file():
        raise InvalidTaggedImageError(f"No se encontró la imagen: {source_path.name}")

    normalized_images_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = normalized_images_dir / f"{safe_filename_fragment(source_path.stem)}_{uuid4().hex}.png"

    try:
        with Image.open(source_path) as source_image:
            source_image.load()
            corrected_image = ImageOps.exif_transpose(source_image)

            if corrected_image.mode in ("RGBA", "LA"):
                normalized_image = corrected_image.convert("RGBA")
            elif corrected_image.mode == "P" and "transparency" in corrected_image.info:
                normalized_image = corrected_image.convert("RGBA")
            else:
                normalized_image = corrected_image.convert("RGB")

            normalized_image.save(normalized_path, format="PNG", optimize=True)

    except UnidentifiedImageError as exc:
        raise InvalidTaggedImageError(
            f"El archivo no contiene una imagen válida: {source_path.name}"
        ) from exc
    except (OSError, ValueError, SyntaxError) as exc:
        raise InvalidTaggedImageError(
            "La imagen está dañada, incompleta o utiliza un formato incompatible: "
            f"{source_path.name}"
        ) from exc

    if not normalized_path.exists() or normalized_path.stat().st_size == 0:
        raise InvalidTaggedImageError(f"No fue posible preparar la imagen: {source_path.name}")

    return normalized_path


def iter_block_paragraphs(container: DocumentObject | _Cell):
    for paragraph in container.paragraphs:
        yield paragraph

    for table in container.tables:
        for row in table.rows:
            for cell in row.cells:
                yield from iter_block_paragraphs(cell)


def clear_paragraph(paragraph: Paragraph) -> None:
    paragraph.text = ""


def insert_paragraph_after(paragraph: Paragraph, text: str = "", style: str | None = None) -> Paragraph:
    new_p = OxmlElement("w:p")
    paragraph._p.addnext(new_p)
    new_paragraph = Paragraph(new_p, paragraph._parent)
    if style:
        try:
            new_paragraph.style = style
        except KeyError:
            pass
    if text:
        new_paragraph.add_run(text)
    return new_paragraph


def insert_table_after(paragraph: Paragraph, rows: int, cols: int) -> Table:
    """
    Inserta una tabla inmediatamente después del párrafo indicado.

    ``paragraph._parent`` puede ser el cuerpo del documento o una celda.
    La API interna del cuerpo requiere ``width``; ``_Cell.add_table()``
    no acepta ese argumento. Se manejan ambos casos explícitamente.
    """

    if rows < 1:
        raise ValueError("La tabla debe tener al menos una fila.")

    if cols < 1:
        raise ValueError("La tabla debe tener al menos una columna.")

    parent = paragraph._parent
    total_width = Mm(160)

    if isinstance(parent, _Cell):
        table = parent.add_table(rows=rows, cols=cols)
    else:
        table = parent.add_table(
            rows=rows,
            cols=cols,
            width=total_width,
        )

    table.autofit = False
    column_width = Mm(160 / cols)

    for column in table.columns:
        column.width = column_width

    for row in table.rows:
        for cell in row.cells:
            cell.width = column_width

    paragraph._p.addnext(table._tbl)

    return table


def set_cell_margins(
    cell: _Cell,
    *,
    top: int = 120,
    start: int = 180,
    bottom: int = 160,
    end: int = 180,
) -> None:
    """Configura márgenes internos de una celda en twips."""

    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")

    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)

    for margin_name, margin_value in {
        "top": top,
        "start": start,
        "bottom": bottom,
        "end": end,
    }.items():
        node = tc_mar.find(qn(f"w:{margin_name}"))
        if node is None:
            node = OxmlElement(f"w:{margin_name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(margin_value))
        node.set(qn("w:type"), "dxa")


def remove_table_borders(table: Table) -> None:
    """Oculta los bordes para que la tabla funcione solo como maquetación."""

    table_pr = table._tbl.tblPr
    borders = table_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        table_pr.append(borders)

    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        edge_node = borders.find(qn(f"w:{edge}"))
        if edge_node is None:
            edge_node = OxmlElement(f"w:{edge}")
            borders.append(edge_node)
        edge_node.set(qn("w:val"), "nil")


def configure_evidence_table(table: Table) -> None:
    """
    Convierte la tabla en una cuadrícula visual limpia de dos columnas.

    Se usa una tabla porque Word necesita un contenedor estable para conservar
    dos evidencias alineadas. Los bordes se ocultan y se agregan márgenes para
    que las fotografías no se vean pegadas ni encimadas.
    """

    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    remove_table_borders(table)

    for row in table.rows:
        row.height = None
        for cell in row.cells:
            cell.width = Mm(78)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            set_cell_margins(cell)


def remove_paragraph_if_empty(paragraph: Paragraph) -> None:
    """Elimina físicamente un párrafo vacío sin afectar los elementos insertados."""

    if (paragraph.text or "").strip():
        return

    paragraph_element = paragraph._element
    parent = paragraph_element.getparent()
    if parent is not None:
        parent.remove(paragraph_element)


def insert_paragraph_after_table(table: Table) -> Paragraph:
    """Crea un párrafo de separación inmediatamente después de una tabla."""

    new_p = OxmlElement("w:p")
    table._tbl.addnext(new_p)
    new_paragraph = Paragraph(new_p, table._parent)
    new_paragraph.paragraph_format.space_after = Pt(6)
    return new_paragraph


GENERATED_TITLE_FONT_SIZE_PT = 11
GENERATED_PHOTO_NAME_FONT_SIZE_PT = 10
GENERATED_BODY_FONT_SIZE_PT = 8
GENERATED_FONT_NAME = "Calibri"
GENERATED_TEXT_COLOR = RGBColor(0, 0, 0)


def apply_calibri_font(
    run,
    size_pt: int,
    *,
    bold: bool | None = None,
    color: RGBColor | None = GENERATED_TEXT_COLOR,
) -> None:
    """
    Aplica la tipografía institucional al contenido generado por M.I.A.

    Se configuran explícitamente las familias internas de Word para evitar
    que una fuente de tema (por ejemplo Calibri Light/Aptos) sustituya la
    fuente solicitada al abrir el documento en diferentes equipos.
    """

    run.font.name = GENERATED_FONT_NAME
    run.font.size = Pt(size_pt)

    if bold is not None:
        run.bold = bold

    if color is not None:
        run.font.color.rgb = color

    r_pr = run._element.get_or_add_rPr()
    r_fonts = r_pr.rFonts
    if r_fonts is None:
        r_fonts = OxmlElement("w:rFonts")
        r_pr.insert(0, r_fonts)

    for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
        r_fonts.set(qn(f"w:{attribute}"), GENERATED_FONT_NAME)


def style_heading(
    paragraph: Paragraph,
    level: int = 2,
    *,
    centered: bool = False,
) -> None:
    """
    Da formato a los títulos NEGROS creados por este módulo.

    - Sección: Calibri 11 pt.
    - Subsección: Calibri 11 pt y centrada.

    Los títulos azules que ya existen en el Word original no pasan por esta
    función y, por lo tanto, no se modifican.
    """

    try:
        paragraph.style = f"Heading {level}"
    except KeyError:
        pass

    if centered:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for run in paragraph.runs:
        apply_calibri_font(
            run,
            GENERATED_TITLE_FONT_SIZE_PT,
            bold=True,
        )


def add_caption(cell: _Cell, text: str) -> None:
    """Título negro colocado encima de cada fotografía."""

    paragraph = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_after = Pt(3)

    run = paragraph.add_run(text)
    apply_calibri_font(
        run,
        GENERATED_PHOTO_NAME_FONT_SIZE_PT,
        bold=True,
    )


def add_small_text(cell: _Cell, text: str) -> None:
    """Texto auxiliar del contenido generado, siempre Calibri 8 pt."""

    if not text:
        return

    paragraph = cell.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(2)

    run = paragraph.add_run(text)
    apply_calibri_font(
        run,
        GENERATED_BODY_FONT_SIZE_PT,
        bold=False,
    )


def add_metadata_line(cell: _Cell, label: str, value: str) -> None:
    """
    Agrega una línea de datos debajo de una fotografía.

    Regla visual solicitada:
    - Etiqueta y valor: Calibri 8 pt.
    - La etiqueta puede ir en negrita para facilitar la lectura.
    """

    value = clean_text(value)
    if not value:
        return

    paragraph = cell.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)

    label_run = paragraph.add_run(label)
    apply_calibri_font(
        label_run,
        GENERATED_BODY_FONT_SIZE_PT,
        bold=True,
    )

    value_run = paragraph.add_run(value)
    apply_calibri_font(
        value_run,
        GENERATED_BODY_FONT_SIZE_PT,
        bold=False,
    )


def add_evidence_metadata(cell: _Cell, evidence: TagEvidenceRow) -> None:
    """
    Agrega debajo de cada fotografía la misma información operativa que se
    utiliza al crear un protocolo C5 nuevo.
    """

    arrival = join_date_and_time(evidence.arrival_date, evidence.arrival_time)
    completion = join_date_and_time(
        evidence.completion_date,
        evidence.completion_time,
    )

    add_metadata_line(cell, "Fecha y hora de arribo: ", arrival)
    add_metadata_line(cell, "Fecha y hora de terminación: ", completion)
    add_metadata_line(cell, "Lugar: ", evidence.location)
    add_metadata_line(cell, "No. De ticket: ", evidence.ticket)


def add_image_to_cell(cell: _Cell, image_path: Path) -> None:
    paragraph = cell.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(3)
    run = paragraph.add_run()
    # Un ancho ligeramente menor deja separación real entre ambas columnas.
    run.add_picture(str(image_path), width=Mm(66))


def add_page_break_after(paragraph: Paragraph) -> Paragraph:
    new_paragraph = insert_paragraph_after(paragraph, "")
    new_paragraph.add_run().add_break(7)
    return new_paragraph


def insert_tag_content(
    anchor: Paragraph,
    group: TagGroup,
    resolved_images: list[dict[str, object]],
) -> None:
    """
    Inserta el bloque que sustituye a una etiqueta.

    Las fotografías se acomodan en una tabla invisible de dos columnas para
    evitar que Word las mueva o superponga. Cada bloque contiene como máximo
    cuatro imágenes.
    """

    cursor = insert_paragraph_after(anchor, group.section)
    style_heading(cursor, level=2)
    cursor.paragraph_format.space_before = Pt(6)
    cursor.paragraph_format.space_after = Pt(5)

    if group.subsection:
        cursor = insert_paragraph_after(cursor, group.subsection)
        style_heading(cursor, level=3, centered=True)
        cursor.paragraph_format.space_before = Pt(4)
        cursor.paragraph_format.space_after = Pt(4)

    if not resolved_images:
        cursor = insert_paragraph_after(
            cursor,
            "No se encontraron evidencias disponibles para esta etiqueta.",
        )
        cursor.paragraph_format.space_after = Pt(8)
        return

    for block_start in range(0, len(resolved_images), MAX_IMAGES_PER_PAGE):
        block = resolved_images[block_start : block_start + MAX_IMAGES_PER_PAGE]

        if block_start > 0:
            cursor = add_page_break_after(cursor)
            cursor = insert_paragraph_after(cursor, f"{group.section} (continuación)")
            style_heading(cursor, level=2)
            if group.subsection:
                cursor = insert_paragraph_after(cursor, group.subsection)
                style_heading(cursor, level=3, centered=True)

        rows = (len(block) + 1) // 2
        table = insert_table_after(cursor, rows=rows, cols=2)
        configure_evidence_table(table)

        for index, item in enumerate(block):
            row_index = index // 2
            col_index = index % 2
            cell = table.cell(row_index, col_index)
            cell.text = ""
            evidence = item["evidence"]
            title = evidence.title or f"Fotografía {evidence.order}"
            add_caption(cell, title)

            if item.get("image_path"):
                add_image_to_cell(cell, Path(item["image_path"]))
            else:
                add_small_text(cell, f"[No encontrada: Orden {evidence.order}]")

            # Muestra los datos operativos debajo de cada fotografía (o debajo
            # del aviso de imagen faltante), de forma consistente con el flujo
            # de creación de un protocolo C5 nuevo.
            add_evidence_metadata(cell, evidence)

            # La columna Descripcion se conserva en el Excel y en el manifiesto
            # por compatibilidad y trazabilidad, pero NO se imprime en el Word.
            # Esto evita leyendas sueltas como:
            # "Fotografía de identificación y número de serie."
            # "Evidencia del etiquetado aplicado al equipo."

        # Limpia la celda sobrante cuando el número de evidencias es impar.
        if len(block) % 2 == 1:
            empty_cell = table.cell(rows - 1, 1)
            empty_cell.text = ""

        cursor = insert_paragraph_after_table(table)


def resolve_group_images(
    group: TagGroup,
    group_folder: Path | None,
    normalized_images_dir: Path,
    diagnostics: dict[str, object],
) -> list[dict[str, object]]:
    resolved: list[dict[str, object]] = []

    for evidence in group.evidences:
        image_path = find_evidence_image(group_folder, evidence.evidence)

        if not image_path:
            diagnostics["imagenes_no_encontradas"].append(
                {
                    "etiqueta": group.tag_key,
                    "seccion": group.section,
                    "subseccion": group.subsection,
                    "evidencia": evidence.evidence,
                    "orden": evidence.order,
                    "nombre_de_foto": evidence.title,
                    "motivo": "No se encontró la imagen correspondiente al valor de Orden dentro de la carpeta de la etiqueta.",
                }
            )
            diagnostics["resumen"]["imagenes_no_encontradas"] += 1
            resolved.append({"evidence": evidence, "image_path": None})
            continue

        try:
            normalized_path = normalize_image_for_docx(image_path, normalized_images_dir)
            diagnostics["resumen"]["imagenes_insertadas"] += 1
            resolved.append({"evidence": evidence, "image_path": normalized_path})
        except InvalidTaggedImageError as exc:
            diagnostics["imagenes_omitidas"].append(
                {
                    "etiqueta": group.tag_key,
                    "seccion": group.section,
                    "subseccion": group.subsection,
                    "evidencia": evidence.evidence,
                    "orden": evidence.order,
                    "nombre_de_foto": evidence.title,
                    "archivo_detectado": str(image_path),
                    "motivo": str(exc),
                }
            )
            diagnostics["resumen"]["imagenes_omitidas_por_dano"] += 1
            resolved.append({"evidence": evidence, "image_path": None})

    return resolved


def build_initial_diagnostics(job_id: str, groups: list[TagGroup]) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "job_id": job_id,
        "estado": "completado",
        "resumen": {
            "etiquetas_solicitadas": len(groups),
            "etiquetas_reemplazadas": 0,
            "etiquetas_no_encontradas": 0,
            "imagenes_insertadas": 0,
            "imagenes_no_encontradas": 0,
            "imagenes_omitidas_por_dano": 0,
        },
        "etiquetas_no_encontradas": [],
        "imagenes_no_encontradas": [],
        "imagenes_omitidas": [],
    }


def generate_document_from_tags(
    excel_path: Path,
    tagged_document_path: Path,
    evidence_zip_path: Path,
    work_dir: Path,
) -> TaggedDocumentResult:
    groups = read_tag_groups_from_excel(Path(excel_path))
    tagged_document_path = Path(tagged_document_path)

    if not tagged_document_path.exists() or not tagged_document_path.is_file():
        raise FileNotFoundError(f"No existe el documento Word: {tagged_document_path}")

    if tagged_document_path.suffix.lower() != ".docx":
        raise ValueError("El documento con etiquetas debe ser un archivo .docx.")

    job_id = uuid4().hex
    job_dir = Path(work_dir) / job_id
    extract_dir = job_dir / "e"
    normalized_images_dir = job_dir / "i"
    output_dir = job_dir / "o"
    output_docx_path = output_dir / TAGGED_OUTPUT_DOCX_FILENAME
    diagnostics_path = output_dir / "diagnostico_etiquetas.json"

    if job_dir.exists():
        shutil.rmtree(job_dir, ignore_errors=True)

    extract_dir.mkdir(parents=True, exist_ok=True)
    normalized_images_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_extract_zip(Path(evidence_zip_path), extract_dir)
    manifest = load_manifest(extract_dir)

    try:
        document = Document(str(tagged_document_path))
    except Exception as exc:
        raise ValueError(
            "No fue posible abrir el documento Word. Verifica que sea un .docx válido."
        ) from exc

    diagnostics = build_initial_diagnostics(job_id, groups)

    for group in groups:
        matching_paragraphs: list[Paragraph] = []
        variants = tag_variants(group.tag_key, group.tag_display)

        for paragraph in iter_block_paragraphs(document):
            paragraph_text = paragraph.text or ""
            if any(token in paragraph_text for token in variants):
                matching_paragraphs.append(paragraph)

        if not matching_paragraphs:
            diagnostics["resumen"]["etiquetas_no_encontradas"] += 1
            diagnostics["etiquetas_no_encontradas"].append(
                {
                    "etiqueta": group.tag_key,
                    "seccion": group.section,
                    "subseccion": group.subsection,
                    "tokens_buscados": variants,
                    "motivo": "No se encontró la etiqueta dentro del documento Word.",
                }
            )
            continue

        group_folder = find_group_folder(extract_dir, group, manifest)
        resolved_images = resolve_group_images(
            group,
            group_folder,
            normalized_images_dir,
            diagnostics,
        )

        for paragraph in matching_paragraphs:
            paragraph_became_empty = remove_tag_marker_from_paragraph(
                paragraph,
                tag_key=group.tag_key,
                tag_display=group.tag_display,
            )

            insert_tag_content(paragraph, group, resolved_images)

            # Cuando la etiqueta ocupaba todo el párrafo, se elimina el párrafo
            # vacío para que no queden llaves, corchetes ni líneas sobrantes.
            if paragraph_became_empty:
                remove_paragraph_if_empty(paragraph)

        diagnostics["resumen"]["etiquetas_reemplazadas"] += 1

    if diagnostics["resumen"]["etiquetas_no_encontradas"] > 0 or diagnostics["resumen"]["imagenes_no_encontradas"] > 0 or diagnostics["resumen"]["imagenes_omitidas_por_dano"] > 0:
        diagnostics["estado"] = "completado_con_observaciones"

    document.save(str(output_docx_path))
    write_text_file(diagnostics_path, json.dumps(diagnostics, ensure_ascii=False, indent=2))

    if not output_docx_path.exists() or output_docx_path.stat().st_size == 0:
        raise RuntimeError("El documento Word con etiquetas no se generó correctamente.")

    return TaggedDocumentResult(
        job_id=job_id,
        output_docx_path=output_docx_path,
        diagnostics_path=diagnostics_path,
        total_tags=len(groups),
        total_tags_replaced=int(diagnostics["resumen"]["etiquetas_reemplazadas"]),
        total_tags_not_found=int(diagnostics["resumen"]["etiquetas_no_encontradas"]),
        total_images_inserted=int(diagnostics["resumen"]["imagenes_insertadas"]),
        total_images_missing=int(diagnostics["resumen"]["imagenes_no_encontradas"]),
        total_images_omitted=int(diagnostics["resumen"]["imagenes_omitidas_por_dano"]),
    )





# from __future__ import annotations

# import datetime as dt
# import json
# import re
# import shutil
# import unicodedata
# import zipfile

# from dataclasses import dataclass
# from pathlib import Path
# from uuid import uuid4

# import pandas as pd

# from PIL import Image, ImageFile, ImageOps, UnidentifiedImageError

# from docx import Document
# from docx.document import Document as DocumentObject
# from docx.oxml import OxmlElement
# from docx.oxml.ns import qn
# from docx.shared import Mm, Pt, RGBColor
# from docx.table import Table, _Cell
# from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
# from docx.enum.text import WD_ALIGN_PARAGRAPH
# from docx.text.paragraph import Paragraph


# ImageFile.LOAD_TRUNCATED_IMAGES = True

# IMAGE_EXTENSIONS = {
#     ".jpg",
#     ".jpeg",
#     ".png",
#     ".bmp",
#     ".tif",
#     ".tiff",
#     ".webp",
#     ".jfif",
# }

# TAG_MANIFEST_FILENAME = "manifest_word_tags.json"
# TAG_STRUCTURE_ZIP_FILENAME = "Estructura_Etiquetas_Word.zip"
# TAGGED_OUTPUT_DOCX_FILENAME = "Documento_Completo_Etiquetas.docx"
# MAX_IMAGES_PER_PAGE = 4


# @dataclass
# class TagEvidenceRow:
#     tag_key: str
#     tag_display: str
#     section: str
#     subsection: str
#     evidence: str
#     title: str
#     description: str

#     # Metadatos operativos que se muestran debajo de cada fotografía.
#     arrival_date: str
#     arrival_time: str
#     completion_date: str
#     completion_time: str
#     location: str
#     ticket: str

#     order: int


# @dataclass
# class TagGroup:
#     tag_key: str
#     tag_display: str
#     section: str
#     subsection: str
#     evidences: list[TagEvidenceRow]


# @dataclass
# class TaggedFoldersResult:
#     job_id: str
#     zip_path: Path
#     manifest_path: Path
#     total_tags: int
#     total_evidences: int


# @dataclass
# class TaggedDocumentResult:
#     job_id: str
#     output_docx_path: Path
#     diagnostics_path: Path
#     total_tags: int
#     total_tags_replaced: int
#     total_tags_not_found: int
#     total_images_inserted: int
#     total_images_missing: int
#     total_images_omitted: int


# class InvalidTaggedImageError(ValueError):
#     """Error controlado para imágenes que no se pueden insertar en Word."""


# class InvalidTaggedExcelError(ValueError):
#     """Error controlado para Excel de etiquetas inválido."""


# def normalizar_texto(value: object) -> str:
#     if pd.isna(value):
#         return ""

#     text = str(value)
#     text = "".join(
#         char
#         for char in unicodedata.normalize("NFD", text)
#         if unicodedata.category(char) != "Mn"
#     )
#     text = text.lower()
#     text = text.replace("-", " ").replace("_", " ")
#     text = re.sub(r"[^a-z0-9 ]", "", text)
#     text = re.sub(r"\s+", " ", text).strip()
#     return text


# def clean_text(value: object) -> str:
#     if pd.isna(value):
#         return ""

#     text = str(value).strip()
#     if text.lower() == "nan":
#         return ""
#     return text


# def format_document_date(value: object) -> str:
#     """
#     Convierte fechas provenientes de Excel al formato dd/mm/aaaa utilizado
#     en los Protocolos C5. Acepta fechas reales de Excel, datetime y texto.
#     """

#     if value is None:
#         return ""

#     try:
#         if pd.isna(value):
#             return ""
#     except (TypeError, ValueError):
#         pass

#     if isinstance(value, pd.Timestamp):
#         return value.strftime("%d/%m/%Y")

#     if isinstance(value, dt.datetime):
#         return value.strftime("%d/%m/%Y")

#     if isinstance(value, dt.date):
#         return value.strftime("%d/%m/%Y")

#     text = clean_text(value)
#     if not text:
#         return ""

#     try:
#         parsed = pd.to_datetime(
#             text,
#             dayfirst=True,
#             errors="coerce",
#         )
#         if not pd.isna(parsed):
#             return parsed.strftime("%d/%m/%Y")
#     except (TypeError, ValueError, OverflowError):
#         pass

#     return text


# def format_document_time(value: object) -> str:
#     """
#     Normaliza horas provenientes de Excel sin obligar al usuario a utilizar
#     un único formato. También soporta la fracción de día usada por Excel.
#     """

#     if value is None:
#         return ""

#     try:
#         if pd.isna(value):
#             return ""
#     except (TypeError, ValueError):
#         pass

#     if isinstance(value, pd.Timestamp):
#         return value.strftime("%H:%M")

#     if isinstance(value, dt.datetime):
#         return value.strftime("%H:%M")

#     if isinstance(value, dt.time):
#         return value.strftime("%H:%M")

#     if isinstance(value, (int, float)) and not isinstance(value, bool):
#         numeric_value = float(value)
#         if 0 <= numeric_value < 1:
#             total_seconds = round(numeric_value * 24 * 60 * 60)
#             hours = (total_seconds // 3600) % 24
#             minutes = (total_seconds % 3600) // 60
#             seconds = total_seconds % 60

#             if seconds:
#                 return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

#             return f"{hours:02d}:{minutes:02d}"

#     return clean_text(value)


# def join_date_and_time(date_value: str, time_value: str) -> str:
#     """Une fecha y hora respetando los casos donde uno de los dos falte."""

#     date_value = clean_text(date_value)
#     time_value = clean_text(time_value)

#     if date_value and time_value:
#         return f"{date_value} a las {time_value}"
#     if date_value:
#         return date_value
#     if time_value:
#         return time_value
#     return ""


# def safe_filename_fragment(value: object, fallback: str = "SIN_NOMBRE") -> str:
#     text = clean_text(value) or fallback
#     text = re.sub(r'[<>:"/\\|?*]', "_", text)
#     text = re.sub(r"\s+", "_", text)
#     text = text.strip(" ._")
#     return text[:120] or fallback


# def extract_tag_key(value: object) -> str:
#     """
#     Convierte una etiqueta escrita como {{TAG}}, [[TAG]], <<TAG>> o TAG
#     en una clave interna estable: TAG.
#     """

#     text = clean_text(value)
#     if not text:
#         return ""

#     wrappers = [
#         ("{{", "}}"),
#         ("[[", "]]"),
#         ("<<", ">>"),
#         ("${", "}"),
#     ]

#     changed = True
#     while changed:
#         changed = False
#         for start, end in wrappers:
#             if text.startswith(start) and text.endswith(end):
#                 text = text[len(start) : -len(end)].strip()
#                 changed = True

#     text = re.sub(r"\s+", "_", text.strip())
#     text = text.strip("{}[]<>")
#     return text


# def tag_variants(tag_key: str, tag_display: str | None = None) -> list[str]:
#     """
#     Devuelve las variantes de una etiqueta en orden seguro.

#     Los marcadores completos se colocan antes que la clave desnuda para evitar
#     que al reemplazar ``PENDIENTE_X`` dentro de ``{{PENDIENTE_X}}`` queden
#     residuos como ``{{}}``.
#     """

#     clean_key = extract_tag_key(tag_key)
#     variants: list[str] = []

#     for candidate in [
#         tag_display or "",
#         f"{{{{{clean_key}}}}}",
#         f"[[{clean_key}]]",
#         f"<<{clean_key}>>",
#         f"${{{clean_key}}}",
#         clean_key,
#     ]:
#         candidate = clean_text(candidate)
#         if candidate and candidate not in variants:
#             variants.append(candidate)

#     return variants


# def remove_tag_marker_from_paragraph(
#     paragraph: Paragraph,
#     tag_key: str,
#     tag_display: str | None = None,
# ) -> bool:
#     """
#     Elimina una etiqueta completa del párrafo, incluso cuando contiene espacios
#     dentro de los delimitadores.

#     También limpia residuos de versiones anteriores, por ejemplo ``{{}}``.
#     Devuelve ``True`` cuando el párrafo queda vacío después de la limpieza.
#     """

#     original_text = paragraph.text or ""
#     cleaned_text = original_text
#     clean_key = extract_tag_key(tag_key)

#     if clean_key:
#         escaped_key = re.escape(clean_key)
#         full_marker_patterns = [
#             rf"\{{\{{\s*{escaped_key}\s*\}}\}}",
#             rf"\[\[\s*{escaped_key}\s*\]\]",
#             rf"<<\s*{escaped_key}\s*>>",
#             rf"\$\{{\s*{escaped_key}\s*\}}",
#         ]

#         for pattern in full_marker_patterns:
#             cleaned_text = re.sub(
#                 pattern,
#                 "",
#                 cleaned_text,
#                 flags=re.IGNORECASE,
#             )

#     display_value = clean_text(tag_display or "")
#     if display_value:
#         cleaned_text = re.sub(
#             re.escape(display_value),
#             "",
#             cleaned_text,
#             flags=re.IGNORECASE,
#         )

#     if clean_key:
#         cleaned_text = re.sub(
#             rf"(?<![A-Za-z0-9_]){re.escape(clean_key)}(?![A-Za-z0-9_])",
#             "",
#             cleaned_text,
#             flags=re.IGNORECASE,
#         )

#     # Limpia delimitadores vacíos que pudieron quedar en documentos generados
#     # con versiones anteriores del sistema.
#     cleaned_text = re.sub(r"\{\{\s*\}\}", "", cleaned_text)
#     cleaned_text = re.sub(r"\[\[\s*\]\]", "", cleaned_text)
#     cleaned_text = re.sub(r"<<\s*>>", "", cleaned_text)
#     cleaned_text = re.sub(r"\$\{\s*\}", "", cleaned_text)
#     cleaned_text = re.sub(r"[ 	]+", " ", cleaned_text)
#     cleaned_text = re.sub(r"\s*\n\s*", "\n", cleaned_text)
#     cleaned_text = cleaned_text.strip()

#     if cleaned_text != original_text:
#         paragraph.text = cleaned_text

#     return not cleaned_text


# def find_column(columns: list[str], aliases: list[str], required_name: str) -> str:
#     normalized = {normalizar_texto(column): column for column in columns}

#     for alias in aliases:
#         key = normalizar_texto(alias)
#         if key in normalized:
#             return normalized[key]

#     raise InvalidTaggedExcelError(
#         "El Excel de etiquetas no contiene la columna requerida: "
#         f"{required_name}."
#     )


# def optional_column(columns: list[str], aliases: list[str]) -> str | None:
#     normalized = {normalizar_texto(column): column for column in columns}

#     for alias in aliases:
#         key = normalizar_texto(alias)
#         if key in normalized:
#             return normalized[key]

#     return None


# def parse_order(value: object, default: int) -> int:
#     if pd.isna(value):
#         return default

#     try:
#         return int(float(str(value).strip()))
#     except (TypeError, ValueError):
#         return default


# def read_tag_groups_from_excel(excel_path: Path) -> list[TagGroup]:
#     excel_path = Path(excel_path)

#     if not excel_path.exists() or not excel_path.is_file():
#         raise FileNotFoundError(f"No existe el Excel de etiquetas: {excel_path}")

#     try:
#         dataframe = pd.read_excel(excel_path, sheet_name=0)
#     except Exception as exc:
#         raise InvalidTaggedExcelError(
#             "No fue posible leer el Excel de etiquetas. Verifica que sea un "
#             "archivo .xlsx válido y que no esté dañado."
#         ) from exc

#     if dataframe.empty:
#         raise InvalidTaggedExcelError("El Excel de etiquetas no contiene registros.")

#     dataframe.columns = dataframe.columns.astype(str).str.strip()
#     columns = list(dataframe.columns)

#     tag_column = find_column(
#         columns,
#         ["Etiqueta", "Tag", "Marcador", "Etiqueta Word", "EtiquetaWord"],
#         "Etiqueta",
#     )
#     section_column = find_column(
#         columns,
#         ["Seccion", "Sección", "Section", "Titulo Seccion", "Título Sección"],
#         "Seccion",
#     )
#     evidence_column = find_column(
#         columns,
#         ["Evidencia", "Foto", "Imagen", "Archivo", "NombreArchivo", "Nombre de archivo"],
#         "Evidencia",
#     )

#     subsection_column = optional_column(
#         columns,
#         ["Subseccion", "Subsección", "Subsection", "Subtitulo", "Subtítulo"],
#     )
#     title_column = optional_column(
#         columns,
#         [
#             "TituloEnDocumento",
#             "TítuloEnDocumento",
#             "Titulo en documento",
#             "Título en documento",
#             "NombreDeImagenEnDocumento",
#             "Nombre en documento",
#             "Titulo Evidencia",
#             "Título Evidencia",
#         ],
#     )
#     description_column = optional_column(
#         columns,
#         ["Descripcion", "Descripción", "Comentario", "Comentarios", "Observacion", "Observación"],
#     )

#     arrival_date_column = optional_column(
#         columns,
#         ["FechaDeArribo", "Fecha de arribo", "Fecha Arribo", "FechaArribo"],
#     )
#     arrival_time_column = optional_column(
#         columns,
#         ["HoraDeArribo", "Hora de arribo", "Hora Arribo", "HoraArribo"],
#     )
#     completion_date_column = optional_column(
#         columns,
#         [
#             "FechaDeTerminación",
#             "FechaDeTerminacion",
#             "Fecha de terminación",
#             "Fecha de terminacion",
#             "FechaTerminacion",
#         ],
#     )
#     completion_time_column = optional_column(
#         columns,
#         [
#             "HoraDeTerminación",
#             "HoraDeTerminacion",
#             "Hora de terminación",
#             "Hora de terminacion",
#             "HoraTerminacion",
#         ],
#     )
#     location_column = optional_column(
#         columns,
#         ["Lugar", "Ubicacion", "Ubicación", "Sitio"],
#     )
#     ticket_column = optional_column(
#         columns,
#         [
#             "NoTicket",
#             "No. De ticket",
#             "No. de ticket",
#             "NumeroTicket",
#             "NúmeroTicket",
#             "Ticket",
#         ],
#     )
#     order_column = optional_column(columns, ["Orden", "No", "Número", "Numero", "Indice", "Índice"])

#     rows: list[TagEvidenceRow] = []

#     for index, row in dataframe.iterrows():
#         tag_display = clean_text(row.get(tag_column, ""))
#         tag_key = extract_tag_key(tag_display)
#         section = clean_text(row.get(section_column, ""))
#         evidence = clean_text(row.get(evidence_column, ""))

#         if not tag_key and not section and not evidence:
#             continue

#         if not tag_key:
#             raise InvalidTaggedExcelError(
#                 f"La fila {index + 2} no tiene etiqueta. Captura un valor como "
#                 "TAG_CONDICION_HERRAJES."
#             )

#         if not section:
#             raise InvalidTaggedExcelError(
#                 f"La fila {index + 2} no tiene sección. Captura el título que "
#                 "se insertará en el Word."
#             )

#         if not evidence:
#             raise InvalidTaggedExcelError(
#                 f"La fila {index + 2} no tiene evidencia. Captura el nombre o "
#                 "número de la fotografía esperada."
#             )

#         rows.append(
#             TagEvidenceRow(
#                 tag_key=tag_key,
#                 tag_display=tag_display or f"{{{{{tag_key}}}}}",
#                 section=section,
#                 subsection=clean_text(row.get(subsection_column, "")) if subsection_column else "",
#                 evidence=evidence,
#                 title=clean_text(row.get(title_column, "")) if title_column else "",
#                 description=clean_text(row.get(description_column, "")) if description_column else "",
#                 arrival_date=(
#                     format_document_date(row.get(arrival_date_column, ""))
#                     if arrival_date_column
#                     else ""
#                 ),
#                 arrival_time=(
#                     format_document_time(row.get(arrival_time_column, ""))
#                     if arrival_time_column
#                     else ""
#                 ),
#                 completion_date=(
#                     format_document_date(row.get(completion_date_column, ""))
#                     if completion_date_column
#                     else ""
#                 ),
#                 completion_time=(
#                     format_document_time(row.get(completion_time_column, ""))
#                     if completion_time_column
#                     else ""
#                 ),
#                 location=(
#                     clean_text(row.get(location_column, ""))
#                     if location_column
#                     else ""
#                 ),
#                 ticket=(
#                     clean_text(row.get(ticket_column, ""))
#                     if ticket_column
#                     else ""
#                 ),
#                 order=parse_order(row.get(order_column, None), index + 1) if order_column else index + 1,
#             )
#         )

#     if not rows:
#         raise InvalidTaggedExcelError("El Excel de etiquetas no contiene filas válidas.")

#     grouped: dict[str, TagGroup] = {}

#     for item in sorted(rows, key=lambda entry: (entry.tag_key, entry.order)):
#         if item.tag_key not in grouped:
#             grouped[item.tag_key] = TagGroup(
#                 tag_key=item.tag_key,
#                 tag_display=item.tag_display,
#                 section=item.section,
#                 subsection=item.subsection,
#                 evidences=[],
#             )

#         grouped[item.tag_key].evidences.append(item)

#     return list(grouped.values())


# def safe_extract_zip(zip_path: Path, extract_dir: Path) -> None:
#     zip_path = Path(zip_path)
#     extract_dir = Path(extract_dir)

#     if not zip_path.exists() or not zip_path.is_file():
#         raise FileNotFoundError(f"No existe el ZIP de evidencias: {zip_path}")

#     if not zipfile.is_zipfile(zip_path):
#         raise ValueError("El archivo de evidencias no es un ZIP válido.")

#     extract_dir.mkdir(parents=True, exist_ok=True)
#     extract_root = extract_dir.resolve()

#     with zipfile.ZipFile(zip_path, "r") as zip_ref:
#         for member in zip_ref.infolist():
#             if member.flag_bits & 0x1:
#                 raise ValueError("El ZIP contiene archivos protegidos con contraseña.")

#             member_name = member.filename.replace("\\", "/")
#             if member_name.startswith("/") or ".." in Path(member_name).parts:
#                 raise ValueError("El ZIP contiene rutas no permitidas.")

#             destination = (extract_dir / member_name).resolve()
#             try:
#                 destination.relative_to(extract_root)
#             except ValueError as exc:
#                 raise ValueError("El ZIP contiene rutas fuera de la carpeta de trabajo.") from exc

#         zip_ref.extractall(extract_dir)


# def write_text_file(path: Path, content: str) -> None:
#     path.parent.mkdir(parents=True, exist_ok=True)
#     path.write_text(content, encoding="utf-8")


# def build_tag_manifest(groups: list[TagGroup]) -> dict[str, object]:
#     return {
#         "schema_version": "1.0",
#         "created_at": dt.datetime.now().isoformat(timespec="seconds"),
#         "description": "Estructura generada para completar un Word mediante etiquetas reemplazables.",
#         "tags": [
#             {
#                 "tag_key": group.tag_key,
#                 "tag_tokens": tag_variants(group.tag_key, group.tag_display),
#                 "section": group.section,
#                 "subsection": group.subsection,
#                 "folder_name": folder_name_for_group(position, group),
#                 "evidences": [
#                     {
#                         "evidence": evidence.evidence,
#                         "title": evidence.title,
#                         "description": evidence.description,
#                         "fecha_arribo": evidence.arrival_date,
#                         "hora_arribo": evidence.arrival_time,
#                         "fecha_terminacion": evidence.completion_date,
#                         "hora_terminacion": evidence.completion_time,
#                         "lugar": evidence.location,
#                         "no_ticket": evidence.ticket,
#                         "order": evidence.order,
#                     }
#                     for evidence in group.evidences
#                 ],
#             }
#             for position, group in enumerate(groups, start=1)
#         ],
#     }


# def folder_name_for_group(position: int, group: TagGroup) -> str:
#     section = safe_filename_fragment(group.section, "SECCION")
#     subsection = safe_filename_fragment(group.subsection, "GENERAL") if group.subsection else "GENERAL"
#     tag_key = safe_filename_fragment(group.tag_key, "TAG")
#     return f"{position:02d}. {tag_key} - {section} - {subsection}"


# def generate_tagged_document_folders(
#     excel_path: Path,
#     work_dir: Path,
# ) -> TaggedFoldersResult:
#     groups = read_tag_groups_from_excel(Path(excel_path))
#     job_id = uuid4().hex
#     job_dir = Path(work_dir) / job_id
#     structure_dir = job_dir / "estructura"
#     output_dir = job_dir / "output"
#     root_dir = structure_dir / "Estructura_Etiquetas_Word"

#     if job_dir.exists():
#         shutil.rmtree(job_dir, ignore_errors=True)

#     root_dir.mkdir(parents=True, exist_ok=True)
#     output_dir.mkdir(parents=True, exist_ok=True)

#     manifest = build_tag_manifest(groups)
#     manifest_path = root_dir / TAG_MANIFEST_FILENAME
#     write_text_file(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))

#     total_evidences = 0

#     for position, group in enumerate(groups, start=1):
#         folder_name = folder_name_for_group(position, group)
#         tag_dir = root_dir / folder_name
#         tag_dir.mkdir(parents=True, exist_ok=True)
#         total_evidences += len(group.evidences)

#         expected_lines = [
#             "COLOCA AQUÍ LAS EVIDENCIAS DE ESTA ETIQUETA",
#             "",
#             f"Etiqueta en Word: {{{{{group.tag_key}}}}}",
#             f"Sección: {group.section}",
#             f"Subsección: {group.subsection or 'General'}",
#             "",
#             "Evidencias esperadas:",
#         ]

#         for evidence in group.evidences:
#             expected_lines.append(
#                 f"- {evidence.evidence}"
#                 + (f" | {evidence.title}" if evidence.title else "")
#             )

#         expected_lines.extend(
#             [
#                 "",
#                 "Notas:",
#                 "- Puedes usar nombres como 1.jpg, 1.0.jpeg, 01.png o el nombre exacto capturado en el Excel.",
#                 "- No elimines este archivo si quieres conservar la guía visual de la carpeta.",
#             ]
#         )

#         write_text_file(tag_dir / "_COLOCAR_EVIDENCIAS_AQUI.txt", "\n".join(expected_lines))

#     zip_path = output_dir / TAG_STRUCTURE_ZIP_FILENAME

#     with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
#         for path in root_dir.rglob("*"):
#             zip_file.write(path, path.relative_to(structure_dir))

#     return TaggedFoldersResult(
#         job_id=job_id,
#         zip_path=zip_path,
#         manifest_path=manifest_path,
#         total_tags=len(groups),
#         total_evidences=total_evidences,
#     )


# def load_manifest(extract_dir: Path) -> dict[str, object] | None:
#     manifests = list(extract_dir.rglob(TAG_MANIFEST_FILENAME))
#     if not manifests:
#         return None

#     try:
#         return json.loads(manifests[0].read_text(encoding="utf-8"))
#     except (OSError, json.JSONDecodeError):
#         return None


# def find_group_folder(
#     extract_dir: Path,
#     group: TagGroup,
#     manifest: dict[str, object] | None,
# ) -> Path | None:
#     if manifest:
#         for item in manifest.get("tags", []):
#             if not isinstance(item, dict):
#                 continue

#             if item.get("tag_key") != group.tag_key:
#                 continue

#             folder_name = clean_text(item.get("folder_name", ""))
#             if folder_name:
#                 matches = [path for path in extract_dir.rglob(folder_name) if path.is_dir()]
#                 if matches:
#                     return matches[0]

#     tag_key_normalized = normalizar_texto(group.tag_key)
#     section_normalized = normalizar_texto(group.section)
#     candidates = [path for path in extract_dir.rglob("*") if path.is_dir()]

#     exact_candidates = [
#         path
#         for path in candidates
#         if tag_key_normalized and tag_key_normalized in normalizar_texto(path.name)
#     ]

#     if exact_candidates:
#         exact_candidates.sort(key=lambda item: len(item.parts))
#         return exact_candidates[0]

#     section_candidates = [
#         path
#         for path in candidates
#         if section_normalized and section_normalized in normalizar_texto(path.name)
#     ]

#     if len(section_candidates) == 1:
#         return section_candidates[0]

#     return None


# def split_known_image_extension(name: str) -> tuple[str, str]:
#     path = Path(name)
#     suffix = path.suffix.lower()
#     if suffix in IMAGE_EXTENSIONS:
#         return path.stem, suffix
#     return name, ""


# def evidence_tokens(value: str) -> set[str]:
#     base, _ = split_known_image_extension(clean_text(value))
#     normalized = normalizar_texto(base)
#     tokens = {normalized} if normalized else set()

#     numeric_match = re.match(r"^(\d+)(?:\.0+)?$", base.strip())
#     if numeric_match:
#         number = int(numeric_match.group(1))
#         tokens.add(str(number))
#         tokens.add(f"{number:02d}")
#         tokens.add(f"{number:03d}")
#         tokens.add(f"{number} 0")

#     return {token for token in tokens if token}


# def image_matches_evidence(image_path: Path, evidence_name: str) -> bool:
#     if image_path.suffix.lower() not in IMAGE_EXTENSIONS:
#         return False

#     expected = evidence_tokens(evidence_name)
#     if not expected:
#         return False

#     image_base, _ = split_known_image_extension(image_path.name)
#     image_normalized = normalizar_texto(image_base)

#     if image_normalized in expected:
#         return True

#     image_parts = set(image_normalized.split())
#     return bool(expected.intersection(image_parts))


# def find_evidence_image(group_folder: Path | None, evidence_name: str) -> Path | None:
#     if not group_folder or not group_folder.exists() or not group_folder.is_dir():
#         return None

#     image_files = [
#         path
#         for path in group_folder.rglob("*")
#         if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
#     ]

#     exact_name = clean_text(evidence_name).casefold()
#     for path in image_files:
#         if path.name.casefold() == exact_name:
#             return path

#     matches = [path for path in image_files if image_matches_evidence(path, evidence_name)]

#     if len(matches) == 1:
#         return matches[0]

#     if len(matches) > 1:
#         matches.sort(key=lambda item: (len(item.parts), item.name.casefold()))
#         return matches[0]

#     return None


# def normalize_image_for_docx(source_path: Path, normalized_images_dir: Path) -> Path:
#     source_path = Path(source_path)
#     normalized_images_dir = Path(normalized_images_dir)

#     if not source_path.exists() or not source_path.is_file():
#         raise InvalidTaggedImageError(f"No se encontró la imagen: {source_path.name}")

#     normalized_images_dir.mkdir(parents=True, exist_ok=True)
#     normalized_path = normalized_images_dir / f"{safe_filename_fragment(source_path.stem)}_{uuid4().hex}.png"

#     try:
#         with Image.open(source_path) as source_image:
#             source_image.load()
#             corrected_image = ImageOps.exif_transpose(source_image)

#             if corrected_image.mode in ("RGBA", "LA"):
#                 normalized_image = corrected_image.convert("RGBA")
#             elif corrected_image.mode == "P" and "transparency" in corrected_image.info:
#                 normalized_image = corrected_image.convert("RGBA")
#             else:
#                 normalized_image = corrected_image.convert("RGB")

#             normalized_image.save(normalized_path, format="PNG", optimize=True)

#     except UnidentifiedImageError as exc:
#         raise InvalidTaggedImageError(
#             f"El archivo no contiene una imagen válida: {source_path.name}"
#         ) from exc
#     except (OSError, ValueError, SyntaxError) as exc:
#         raise InvalidTaggedImageError(
#             "La imagen está dañada, incompleta o utiliza un formato incompatible: "
#             f"{source_path.name}"
#         ) from exc

#     if not normalized_path.exists() or normalized_path.stat().st_size == 0:
#         raise InvalidTaggedImageError(f"No fue posible preparar la imagen: {source_path.name}")

#     return normalized_path


# def iter_block_paragraphs(container: DocumentObject | _Cell):
#     for paragraph in container.paragraphs:
#         yield paragraph

#     for table in container.tables:
#         for row in table.rows:
#             for cell in row.cells:
#                 yield from iter_block_paragraphs(cell)


# def clear_paragraph(paragraph: Paragraph) -> None:
#     paragraph.text = ""


# def insert_paragraph_after(paragraph: Paragraph, text: str = "", style: str | None = None) -> Paragraph:
#     new_p = OxmlElement("w:p")
#     paragraph._p.addnext(new_p)
#     new_paragraph = Paragraph(new_p, paragraph._parent)
#     if style:
#         try:
#             new_paragraph.style = style
#         except KeyError:
#             pass
#     if text:
#         new_paragraph.add_run(text)
#     return new_paragraph


# def insert_table_after(paragraph: Paragraph, rows: int, cols: int) -> Table:
#     """
#     Inserta una tabla inmediatamente después del párrafo indicado.

#     ``paragraph._parent`` puede ser el cuerpo del documento o una celda.
#     La API interna del cuerpo requiere ``width``; ``_Cell.add_table()``
#     no acepta ese argumento. Se manejan ambos casos explícitamente.
#     """

#     if rows < 1:
#         raise ValueError("La tabla debe tener al menos una fila.")

#     if cols < 1:
#         raise ValueError("La tabla debe tener al menos una columna.")

#     parent = paragraph._parent
#     total_width = Mm(160)

#     if isinstance(parent, _Cell):
#         table = parent.add_table(rows=rows, cols=cols)
#     else:
#         table = parent.add_table(
#             rows=rows,
#             cols=cols,
#             width=total_width,
#         )

#     table.autofit = False
#     column_width = Mm(160 / cols)

#     for column in table.columns:
#         column.width = column_width

#     for row in table.rows:
#         for cell in row.cells:
#             cell.width = column_width

#     paragraph._p.addnext(table._tbl)

#     return table


# def set_cell_margins(
#     cell: _Cell,
#     *,
#     top: int = 120,
#     start: int = 180,
#     bottom: int = 160,
#     end: int = 180,
# ) -> None:
#     """Configura márgenes internos de una celda en twips."""

#     tc = cell._tc
#     tc_pr = tc.get_or_add_tcPr()
#     tc_mar = tc_pr.first_child_found_in("w:tcMar")

#     if tc_mar is None:
#         tc_mar = OxmlElement("w:tcMar")
#         tc_pr.append(tc_mar)

#     for margin_name, margin_value in {
#         "top": top,
#         "start": start,
#         "bottom": bottom,
#         "end": end,
#     }.items():
#         node = tc_mar.find(qn(f"w:{margin_name}"))
#         if node is None:
#             node = OxmlElement(f"w:{margin_name}")
#             tc_mar.append(node)
#         node.set(qn("w:w"), str(margin_value))
#         node.set(qn("w:type"), "dxa")


# def remove_table_borders(table: Table) -> None:
#     """Oculta los bordes para que la tabla funcione solo como maquetación."""

#     table_pr = table._tbl.tblPr
#     borders = table_pr.first_child_found_in("w:tblBorders")
#     if borders is None:
#         borders = OxmlElement("w:tblBorders")
#         table_pr.append(borders)

#     for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
#         edge_node = borders.find(qn(f"w:{edge}"))
#         if edge_node is None:
#             edge_node = OxmlElement(f"w:{edge}")
#             borders.append(edge_node)
#         edge_node.set(qn("w:val"), "nil")


# def configure_evidence_table(table: Table) -> None:
#     """
#     Convierte la tabla en una cuadrícula visual limpia de dos columnas.

#     Se usa una tabla porque Word necesita un contenedor estable para conservar
#     dos evidencias alineadas. Los bordes se ocultan y se agregan márgenes para
#     que las fotografías no se vean pegadas ni encimadas.
#     """

#     table.alignment = WD_TABLE_ALIGNMENT.CENTER
#     table.autofit = False
#     remove_table_borders(table)

#     for row in table.rows:
#         row.height = None
#         for cell in row.cells:
#             cell.width = Mm(78)
#             cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
#             set_cell_margins(cell)


# def remove_paragraph_if_empty(paragraph: Paragraph) -> None:
#     """Elimina físicamente un párrafo vacío sin afectar los elementos insertados."""

#     if (paragraph.text or "").strip():
#         return

#     paragraph_element = paragraph._element
#     parent = paragraph_element.getparent()
#     if parent is not None:
#         parent.remove(paragraph_element)


# def insert_paragraph_after_table(table: Table) -> Paragraph:
#     """Crea un párrafo de separación inmediatamente después de una tabla."""

#     new_p = OxmlElement("w:p")
#     table._tbl.addnext(new_p)
#     new_paragraph = Paragraph(new_p, table._parent)
#     new_paragraph.paragraph_format.space_after = Pt(6)
#     return new_paragraph


# def style_heading(paragraph: Paragraph, level: int = 2) -> None:
#     try:
#         paragraph.style = f"Heading {level}"
#     except KeyError:
#         pass

#     if paragraph.runs:
#         run = paragraph.runs[0]
#         run.font.bold = True
#         run.font.color.rgb = RGBColor(15, 23, 42)


# def add_caption(cell: _Cell, text: str) -> None:
#     paragraph = cell.paragraphs[0] if cell.paragraphs else cell.add_paragraph()
#     paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
#     paragraph.paragraph_format.space_after = Pt(3)
#     run = paragraph.add_run(text)
#     run.bold = True
#     run.font.size = Pt(8)
#     run.font.color.rgb = RGBColor(15, 23, 42)


# def add_small_text(cell: _Cell, text: str) -> None:
#     if not text:
#         return
#     paragraph = cell.add_paragraph()
#     paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
#     paragraph.paragraph_format.space_before = Pt(3)
#     paragraph.paragraph_format.space_after = Pt(2)
#     run = paragraph.add_run(text)
#     run.font.size = Pt(8)
#     run.font.color.rgb = RGBColor(71, 85, 105)


# def add_metadata_line(cell: _Cell, label: str, value: str) -> None:
#     """Agrega una línea de metadatos operativos debajo de una fotografía."""

#     value = clean_text(value)
#     if not value:
#         return

#     paragraph = cell.add_paragraph()
#     paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
#     paragraph.paragraph_format.space_before = Pt(0)
#     paragraph.paragraph_format.space_after = Pt(0)

#     label_run = paragraph.add_run(label)
#     label_run.bold = True
#     label_run.font.size = Pt(8)
#     label_run.font.color.rgb = RGBColor(15, 23, 42)

#     value_run = paragraph.add_run(value)
#     value_run.font.size = Pt(8)
#     value_run.font.color.rgb = RGBColor(15, 23, 42)


# def add_evidence_metadata(cell: _Cell, evidence: TagEvidenceRow) -> None:
#     """
#     Agrega debajo de cada evidencia la misma información operativa que se
#     utiliza al crear un protocolo C5 nuevo.
#     """

#     arrival = join_date_and_time(evidence.arrival_date, evidence.arrival_time)
#     completion = join_date_and_time(
#         evidence.completion_date,
#         evidence.completion_time,
#     )

#     add_metadata_line(cell, "Fecha y hora de arribo: ", arrival)
#     add_metadata_line(cell, "Fecha y hora de terminación: ", completion)
#     add_metadata_line(cell, "Lugar: ", evidence.location)
#     add_metadata_line(cell, "No. De ticket: ", evidence.ticket)


# def add_image_to_cell(cell: _Cell, image_path: Path) -> None:
#     paragraph = cell.add_paragraph()
#     paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
#     paragraph.paragraph_format.space_before = Pt(2)
#     paragraph.paragraph_format.space_after = Pt(3)
#     run = paragraph.add_run()
#     # Un ancho ligeramente menor deja separación real entre ambas columnas.
#     run.add_picture(str(image_path), width=Mm(66))


# def add_page_break_after(paragraph: Paragraph) -> Paragraph:
#     new_paragraph = insert_paragraph_after(paragraph, "")
#     new_paragraph.add_run().add_break(7)
#     return new_paragraph


# def insert_tag_content(
#     anchor: Paragraph,
#     group: TagGroup,
#     resolved_images: list[dict[str, object]],
# ) -> None:
#     """
#     Inserta el bloque que sustituye a una etiqueta.

#     Las fotografías se acomodan en una tabla invisible de dos columnas para
#     evitar que Word las mueva o superponga. Cada bloque contiene como máximo
#     cuatro imágenes.
#     """

#     cursor = insert_paragraph_after(anchor, group.section)
#     style_heading(cursor, level=2)
#     cursor.paragraph_format.space_before = Pt(6)
#     cursor.paragraph_format.space_after = Pt(5)

#     if group.subsection:
#         cursor = insert_paragraph_after(cursor, group.subsection)
#         style_heading(cursor, level=3)
#         cursor.paragraph_format.space_before = Pt(4)
#         cursor.paragraph_format.space_after = Pt(4)

#     if not resolved_images:
#         cursor = insert_paragraph_after(
#             cursor,
#             "No se encontraron evidencias disponibles para esta etiqueta.",
#         )
#         cursor.paragraph_format.space_after = Pt(8)
#         return

#     for block_start in range(0, len(resolved_images), MAX_IMAGES_PER_PAGE):
#         block = resolved_images[block_start : block_start + MAX_IMAGES_PER_PAGE]

#         if block_start > 0:
#             cursor = add_page_break_after(cursor)
#             cursor = insert_paragraph_after(cursor, f"{group.section} (continuación)")
#             style_heading(cursor, level=2)
#             if group.subsection:
#                 cursor = insert_paragraph_after(cursor, group.subsection)
#                 style_heading(cursor, level=3)

#         rows = (len(block) + 1) // 2
#         table = insert_table_after(cursor, rows=rows, cols=2)
#         configure_evidence_table(table)

#         for index, item in enumerate(block):
#             row_index = index // 2
#             col_index = index % 2
#             cell = table.cell(row_index, col_index)
#             cell.text = ""
#             evidence = item["evidence"]
#             title = evidence.title or f"Evidencia {evidence.evidence}"
#             add_caption(cell, title)

#             if item.get("image_path"):
#                 add_image_to_cell(cell, Path(item["image_path"]))
#             else:
#                 add_small_text(cell, f"[No encontrada: {evidence.evidence}]")

#             # Muestra los datos operativos debajo de cada fotografía (o debajo
#             # del aviso de imagen faltante), de forma consistente con el flujo
#             # de creación de un protocolo C5 nuevo.
#             add_evidence_metadata(cell, evidence)

#             add_small_text(cell, evidence.description)

#         # Limpia la celda sobrante cuando el número de evidencias es impar.
#         if len(block) % 2 == 1:
#             empty_cell = table.cell(rows - 1, 1)
#             empty_cell.text = ""

#         cursor = insert_paragraph_after_table(table)


# def resolve_group_images(
#     group: TagGroup,
#     group_folder: Path | None,
#     normalized_images_dir: Path,
#     diagnostics: dict[str, object],
# ) -> list[dict[str, object]]:
#     resolved: list[dict[str, object]] = []

#     for evidence in group.evidences:
#         image_path = find_evidence_image(group_folder, evidence.evidence)

#         if not image_path:
#             diagnostics["imagenes_no_encontradas"].append(
#                 {
#                     "etiqueta": group.tag_key,
#                     "seccion": group.section,
#                     "subseccion": group.subsection,
#                     "evidencia": evidence.evidence,
#                     "motivo": "No se encontró la imagen dentro de la carpeta de la etiqueta.",
#                 }
#             )
#             diagnostics["resumen"]["imagenes_no_encontradas"] += 1
#             resolved.append({"evidence": evidence, "image_path": None})
#             continue

#         try:
#             normalized_path = normalize_image_for_docx(image_path, normalized_images_dir)
#             diagnostics["resumen"]["imagenes_insertadas"] += 1
#             resolved.append({"evidence": evidence, "image_path": normalized_path})
#         except InvalidTaggedImageError as exc:
#             diagnostics["imagenes_omitidas"].append(
#                 {
#                     "etiqueta": group.tag_key,
#                     "seccion": group.section,
#                     "subseccion": group.subsection,
#                     "evidencia": evidence.evidence,
#                     "archivo_detectado": str(image_path),
#                     "motivo": str(exc),
#                 }
#             )
#             diagnostics["resumen"]["imagenes_omitidas_por_dano"] += 1
#             resolved.append({"evidence": evidence, "image_path": None})

#     return resolved


# def build_initial_diagnostics(job_id: str, groups: list[TagGroup]) -> dict[str, object]:
#     return {
#         "schema_version": "1.0",
#         "job_id": job_id,
#         "estado": "completado",
#         "resumen": {
#             "etiquetas_solicitadas": len(groups),
#             "etiquetas_reemplazadas": 0,
#             "etiquetas_no_encontradas": 0,
#             "imagenes_insertadas": 0,
#             "imagenes_no_encontradas": 0,
#             "imagenes_omitidas_por_dano": 0,
#         },
#         "etiquetas_no_encontradas": [],
#         "imagenes_no_encontradas": [],
#         "imagenes_omitidas": [],
#     }


# def generate_document_from_tags(
#     excel_path: Path,
#     tagged_document_path: Path,
#     evidence_zip_path: Path,
#     work_dir: Path,
# ) -> TaggedDocumentResult:
#     groups = read_tag_groups_from_excel(Path(excel_path))
#     tagged_document_path = Path(tagged_document_path)

#     if not tagged_document_path.exists() or not tagged_document_path.is_file():
#         raise FileNotFoundError(f"No existe el documento Word: {tagged_document_path}")

#     if tagged_document_path.suffix.lower() != ".docx":
#         raise ValueError("El documento con etiquetas debe ser un archivo .docx.")

#     job_id = uuid4().hex
#     job_dir = Path(work_dir) / job_id
#     extract_dir = job_dir / "e"
#     normalized_images_dir = job_dir / "i"
#     output_dir = job_dir / "o"
#     output_docx_path = output_dir / TAGGED_OUTPUT_DOCX_FILENAME
#     diagnostics_path = output_dir / "diagnostico_etiquetas.json"

#     if job_dir.exists():
#         shutil.rmtree(job_dir, ignore_errors=True)

#     extract_dir.mkdir(parents=True, exist_ok=True)
#     normalized_images_dir.mkdir(parents=True, exist_ok=True)
#     output_dir.mkdir(parents=True, exist_ok=True)

#     safe_extract_zip(Path(evidence_zip_path), extract_dir)
#     manifest = load_manifest(extract_dir)

#     try:
#         document = Document(str(tagged_document_path))
#     except Exception as exc:
#         raise ValueError(
#             "No fue posible abrir el documento Word. Verifica que sea un .docx válido."
#         ) from exc

#     diagnostics = build_initial_diagnostics(job_id, groups)

#     for group in groups:
#         matching_paragraphs: list[Paragraph] = []
#         variants = tag_variants(group.tag_key, group.tag_display)

#         for paragraph in iter_block_paragraphs(document):
#             paragraph_text = paragraph.text or ""
#             if any(token in paragraph_text for token in variants):
#                 matching_paragraphs.append(paragraph)

#         if not matching_paragraphs:
#             diagnostics["resumen"]["etiquetas_no_encontradas"] += 1
#             diagnostics["etiquetas_no_encontradas"].append(
#                 {
#                     "etiqueta": group.tag_key,
#                     "seccion": group.section,
#                     "subseccion": group.subsection,
#                     "tokens_buscados": variants,
#                     "motivo": "No se encontró la etiqueta dentro del documento Word.",
#                 }
#             )
#             continue

#         group_folder = find_group_folder(extract_dir, group, manifest)
#         resolved_images = resolve_group_images(
#             group,
#             group_folder,
#             normalized_images_dir,
#             diagnostics,
#         )

#         for paragraph in matching_paragraphs:
#             paragraph_became_empty = remove_tag_marker_from_paragraph(
#                 paragraph,
#                 tag_key=group.tag_key,
#                 tag_display=group.tag_display,
#             )

#             insert_tag_content(paragraph, group, resolved_images)

#             # Cuando la etiqueta ocupaba todo el párrafo, se elimina el párrafo
#             # vacío para que no queden llaves, corchetes ni líneas sobrantes.
#             if paragraph_became_empty:
#                 remove_paragraph_if_empty(paragraph)

#         diagnostics["resumen"]["etiquetas_reemplazadas"] += 1

#     if diagnostics["resumen"]["etiquetas_no_encontradas"] > 0 or diagnostics["resumen"]["imagenes_no_encontradas"] > 0 or diagnostics["resumen"]["imagenes_omitidas_por_dano"] > 0:
#         diagnostics["estado"] = "completado_con_observaciones"

#     document.save(str(output_docx_path))
#     write_text_file(diagnostics_path, json.dumps(diagnostics, ensure_ascii=False, indent=2))

#     if not output_docx_path.exists() or output_docx_path.stat().st_size == 0:
#         raise RuntimeError("El documento Word con etiquetas no se generó correctamente.")

#     return TaggedDocumentResult(
#         job_id=job_id,
#         output_docx_path=output_docx_path,
#         diagnostics_path=diagnostics_path,
#         total_tags=len(groups),
#         total_tags_replaced=int(diagnostics["resumen"]["etiquetas_reemplazadas"]),
#         total_tags_not_found=int(diagnostics["resumen"]["etiquetas_no_encontradas"]),
#         total_images_inserted=int(diagnostics["resumen"]["imagenes_insertadas"]),
#         total_images_missing=int(diagnostics["resumen"]["imagenes_no_encontradas"]),
#         total_images_omitted=int(diagnostics["resumen"]["imagenes_omitidas_por_dano"]),
#     )

