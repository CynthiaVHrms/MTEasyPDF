import os
import shutil
import zipfile

from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .models import ReportGenerationRequest, ReportGenerationResult

from .file_engine import (
    limpiar_temp,
    extraer_zip,
    obtener_carpeta_raiz,
    clasificar_archivos,
    build_mantenimiento_tree,
    agrupar_pdfs_por_categoria,
    calcular_paginas_indice,
)

from .pdf_utils import (
    draw_images,
    draw_images_by_rows,
    build_pdf_tree,
    MARGIN,
    TOP_SAFE_MARGIN,
)

from .pdf_layout import (
    draw_cover,
    draw_header_footer,
    draw_section_title,
    draw_subsection_title,
    nueva_pagina_con_titulo,
    draw_index,
    draw_introduccion,
    render_documentacion_links,
)



PAGE_WIDTH, PAGE_HEIGHT = A4
TEXT_HEIGHT = 14
TITLE_HEIGHT = 22
MIN_SPACE_AFTER_TITLE = 150


try:
    pdfmetrics.registerFont(TTFont("Arial", "arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", "arialbd.ttf"))
    FUENTE_TEXTO = "Arial"
    FUENTE_NEGRITA = "Arial-Bold"
except Exception:
    FUENTE_TEXTO = "Helvetica"
    FUENTE_NEGRITA = "Helvetica-Bold"


class IndexCollector:
    def __init__(self):
        self.items = []

    def add(self, title, page, level=1):
        self.items.append(
            {
                "title": title,
                "page": page,
                "level": level,
            }
        )

    def get_items(self):
        return self.items


def _report_progress(request: ReportGenerationRequest, value: int) -> None:
    if request.progress_callback:
        request.progress_callback(value)


def render_mantenimiento(
    canvas_obj,
    cursor_y,
    tree,
    pdf_tree,
    project_data,
    index=None,
    insert_tasks=None,
    usa_ubicacion=True,
    callback_progreso=None,
):
    min_bottom = 120
    imagenes_procesadas_ref = [0]

    total_imagenes = 0
    for subsecciones in tree.values():
        for grupos in subsecciones.values():
            for categorias in grupos.values():
                for imagenes in categorias.values():
                    total_imagenes += len(
                        [
                            f
                            for f in imagenes
                            if f.lower().endswith((".jpg", ".jpeg", ".png"))
                        ]
                    )

    for i_sec, (seccion, subsecciones) in enumerate(tree.items()):
        cursor_y = nueva_pagina_con_titulo(canvas_obj, project_data, seccion)

        if index:
            index.add(seccion, canvas_obj.getPageNumber(), level=1)

        for i_sub, (subseccion, grupos) in enumerate(subsecciones.items()):
            if usa_ubicacion and i_sub > 0:
                canvas_obj.showPage()
                draw_header_footer(canvas_obj, canvas_obj.getPageNumber(), project_data)
                cursor_y = draw_section_title(canvas_obj, seccion, TOP_SAFE_MARGIN)

            if subseccion != "__SIN_UBICACION__" and usa_ubicacion:
                cursor_y = draw_subsection_title(canvas_obj, subseccion, cursor_y)

                if index:
                    index.add(subseccion, canvas_obj.getPageNumber(), level=2)

            for i_gru, (grupo, categorias) in enumerate(grupos.items()):
                if not usa_ubicacion:
                    if not (i_sub == 0 and i_gru == 0):
                        canvas_obj.showPage()
                        draw_header_footer(
                            canvas_obj,
                            canvas_obj.getPageNumber(),
                            project_data,
                        )
                        cursor_y = draw_section_title(
                            canvas_obj,
                            seccion,
                            TOP_SAFE_MARGIN,
                        )

                if cursor_y < (min_bottom + TITLE_HEIGHT + MIN_SPACE_AFTER_TITLE):
                    canvas_obj.showPage()
                    draw_header_footer(canvas_obj, canvas_obj.getPageNumber(), project_data)
                    cursor_y = draw_section_title(canvas_obj, seccion, TOP_SAFE_MARGIN)

                if grupo:
                    cursor_y = draw_subsection_title(canvas_obj, grupo, cursor_y)

                    if index:
                        index.add(grupo, canvas_obj.getPageNumber(), level=3)

                for categoria, imagenes_nativas in categorias.items():
                    imgs_cat = [
                        f
                        for f in imagenes_nativas
                        if f.lower().endswith((".jpg", ".jpeg", ".png"))
                    ]

                    if not imgs_cat:
                        continue

                    if categoria:
                        niveles_texto = [
                            str(seccion),
                            str(subseccion),
                            str(grupo),
                            str(categoria),
                        ]

                        txt_busqueda = " ".join(niveles_texto).lower()
                        is_full_width = (
                            "pantalla" in txt_busqueda
                            or "pruebas" in txt_busqueda
                        )

                        max_h = 240 if is_full_width else 220
                        row_gap = max_h + TEXT_HEIGHT + 30
                        bottom_limit = 80
                        altura_necesaria = 22 + row_gap

                        if cursor_y - altura_necesaria < bottom_limit:
                            canvas_obj.showPage()
                            draw_header_footer(
                                canvas_obj,
                                canvas_obj.getPageNumber(),
                                project_data,
                            )
                            cursor_y = draw_section_title(
                                canvas_obj,
                                seccion,
                                TOP_SAFE_MARGIN,
                            )

                        cursor_y = draw_subsection_title(
                            canvas_obj,
                            categoria,
                            cursor_y,
                        )

                    niveles_texto = [
                        str(seccion),
                        str(subseccion),
                        str(grupo),
                        str(categoria),
                    ]

                    txt_busqueda = " ".join(niveles_texto).lower()

                    is_full_width = (
                        "pantalla" in txt_busqueda
                        or "pruebas" in txt_busqueda
                    )

                    num_fotos_fila = 1 if is_full_width else 2

                    cursor_y = draw_images_by_rows(
                        canvas_obj,
                        imgs_cat,
                        images_per_row=num_fotos_fila,
                        start_y=cursor_y,
                        project_data=project_data,
                        seccion=seccion,
                        callback_progreso=callback_progreso,
                        total_imagenes=total_imagenes,
                        imagenes_procesadas_ref=imagenes_procesadas_ref,
                    )

    return cursor_y



def generate_report(request: ReportGenerationRequest) -> ReportGenerationResult:
    project_data = request.project_data
    zip_path = request.zip_path
    temp_dir = request.temp_dir
    output_dir = request.output_dir
    usa_ubicacion = request.usa_ubicacion

    if not project_data.get("titulo"):
        raise ValueError("El campo 'titulo' es obligatorio.")

    if not zip_path.exists():
        raise FileNotFoundError(f"No existe el ZIP: {zip_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    tmp_collector_pdf = output_dir / "_tmp_recolector.pdf"
    tmp_main_pdf = output_dir / "mvp_imagenes.pdf"

    delivery_dir = output_dir / "Reporte_Final_Entrega"
    anexos_dir = delivery_dir / "anexos"
    main_pdf_path = delivery_dir / "Reporte_Principal.pdf"
    final_zip_path = output_dir / "Memoria_Tecnica_Final.zip"

    _report_progress(request, 10)

    limpiar_temp(str(temp_dir))
    extraer_zip(str(zip_path), str(temp_dir))

    raiz = obtener_carpeta_raiz(str(temp_dir))
    data = clasificar_archivos(raiz)

    mantenimiento_tree = build_mantenimiento_tree(
        data["mantenimiento"]["imagenes"],
        raiz,
        usa_ubicacion=usa_ubicacion,
    )

    pdf_tree = build_pdf_tree(
        data["mantenimiento"]["pdfs"],
        raiz,
        usa_ubicacion=usa_ubicacion,
    )

    pdfs_mantenimiento_tree = agrupar_pdfs_por_categoria(
        data["mantenimiento"]["pdfs"],
        raiz,
        usa_ubicacion=usa_ubicacion,
    )

    _report_progress(request, 25)

    index = IndexCollector()

    c = canvas.Canvas(str(tmp_collector_pdf), pagesize=A4)

    draw_cover(c, project_data, project_data)

    draw_header_footer(c, c.getPageNumber(), project_data)
    draw_introduccion(c, project_data.get("introduccion", ""), project_data)
    c.showPage()

    num_paginas_idx = calcular_paginas_indice(
        mantenimiento_tree,
        data,
        usa_ubicacion=usa_ubicacion,
    )

    for _ in range(num_paginas_idx):
        if usa_ubicacion:
            c.showPage()

    if usa_ubicacion and data.get("ubicacion"):
        index.add("Ubicación", c.getPageNumber(), level=1)
        imagenes_restantes = data["ubicacion"][:]

        while imagenes_restantes:
            draw_header_footer(c, c.getPageNumber(), project_data)
            cursor_y = draw_section_title(c, "Ubicación")
            cursor_y -= 20

            per_page = 1 if len(imagenes_restantes) == 1 else 2

            imagenes_restantes, used_height = draw_images(
                c,
                imagenes_restantes,
                per_page=per_page,
                start_y=cursor_y,
            )

            if imagenes_restantes:
                c.showPage()

    if data["inventario"]:
        for pdf in data["inventario"]:
            c.showPage()

            if pdf == data["inventario"][0]:
                index.add("Inventario", c.getPageNumber(), level=1)

            if os.path.exists(pdf):
                reader_temp = PdfReader(pdf)
                for _ in range(len(reader_temp.pages) - 1):
                    c.showPage()

    render_mantenimiento(
        c,
        PAGE_HEIGHT - 100,
        mantenimiento_tree,
        pdfs_mantenimiento_tree,
        project_data,
        index=index,
        insert_tasks=None,
        usa_ubicacion=usa_ubicacion,
        callback_progreso=None,
    )

    render_documentacion_links(
        c,
        PAGE_HEIGHT - 100,
        pdfs_mantenimiento_tree,
        project_data,
        index=index,
    )

    c.showPage()
    index.add("Anexos", c.getPageNumber(), level=1)

    c.save()

    index_items = index.get_items()

    _report_progress(request, 45)

    insert_tasks = []

    c = canvas.Canvas(str(tmp_main_pdf), pagesize=A4, pageCompression=1)

    draw_cover(c, project_data, project_data)

    draw_header_footer(c, c.getPageNumber(), project_data)
    draw_introduccion(c, project_data.get("introduccion", ""), project_data)
    c.showPage()

    draw_header_footer(c, c.getPageNumber(), project_data)
    draw_index(c, index_items, project_data)

    if usa_ubicacion and data.get("ubicacion"):
        imagenes_restantes = data["ubicacion"][:]

        while imagenes_restantes:
            draw_header_footer(c, c.getPageNumber(), project_data)
            cursor_y = draw_section_title(c, "Ubicación")
            cursor_y -= 20

            per_page = 1 if len(imagenes_restantes) == 1 else 2

            imagenes_restantes, used_height = draw_images(
                c,
                imagenes_restantes,
                per_page=per_page,
                start_y=cursor_y,
            )

            if imagenes_restantes:
                c.showPage()

        c.showPage()

    for i, pdf in enumerate(data["inventario"]):
        if i > 0:
            c.showPage()

        p_actual = c.getPageNumber()
        draw_header_footer(c, p_actual, project_data)

        insert_tasks.append((p_actual, pdf))

        c.setFont(FUENTE_NEGRITA, 14)
        c.drawString(
            MARGIN,
            PAGE_HEIGHT - 120,
            f"Documento: {os.path.basename(pdf)}",
        )

        if os.path.exists(pdf):
            reader_temp = PdfReader(pdf)
            paginas_pdf = len(reader_temp.pages)

            for _ in range(paginas_pdf - 1):
                c.showPage()

    render_mantenimiento(
        c,
        PAGE_HEIGHT - 100,
        mantenimiento_tree,
        pdfs_mantenimiento_tree,
        project_data,
        index=None,
        insert_tasks=insert_tasks,
        usa_ubicacion=usa_ubicacion,
        callback_progreso=request.progress_callback,
    )

    render_documentacion_links(
        c,
        PAGE_HEIGHT - 100,
        pdfs_mantenimiento_tree,
        project_data,
        index=None,
    )

    c.showPage()
    draw_header_footer(c, c.getPageNumber(), project_data)

    cursor_y = draw_section_title(c, "Anexos del Proyecto", PAGE_HEIGHT - 100)
    cursor_y -= 20

    c.setFont(FUENTE_TEXTO, 12)

    for pdf in data["anexos"]:
        nombre = os.path.basename(pdf)

        c.setFillColor("blue")
        c.drawString(MARGIN + 20, cursor_y, f"• {nombre}")

        c.linkURL(
            f"anexos/{nombre}",
            (MARGIN + 20, cursor_y, MARGIN + 350, cursor_y + 12),
        )

        cursor_y -= 25

        if cursor_y < 120:
            c.showPage()
            draw_header_footer(c, c.getPageNumber(), project_data)
            cursor_y = PAGE_HEIGHT - 120

    c.save()

    _report_progress(request, 70)

    reader = PdfReader(str(tmp_main_pdf))
    writer = PdfWriter()

    tareas_dict = {p[0]: p[1] for p in insert_tasks}
    skip_until = -1

    for i, page in enumerate(reader.pages):
        num_pdf = i + 1

        if num_pdf <= skip_until:
            continue

        if num_pdf in tareas_dict:
            ruta_pdf_real = tareas_dict[num_pdf]

            if os.path.exists(ruta_pdf_real):
                ext_reader = PdfReader(ruta_pdf_real)

                for page_ext in ext_reader.pages:
                    writer.add_page(page_ext)

                skip_until = num_pdf + len(ext_reader.pages) - 1
            else:
                writer.add_page(page)
        else:
            writer.add_page(page)

    if delivery_dir.exists():
        shutil.rmtree(delivery_dir)

    anexos_dir.mkdir(parents=True, exist_ok=True)

    if reader.metadata:
        writer.add_metadata(reader.metadata)

    with open(main_pdf_path, "wb") as f:
        writer.write(f)

    archivos_para_zip = [main_pdf_path]

    for pdf_anexo in data.get("anexos", []):
        if os.path.exists(pdf_anexo):
            archivos_para_zip.append(Path(pdf_anexo))

    for seccion, subsecciones in pdf_tree.items():
        for subseccion, grupos in subsecciones.items():
            for grupo, categorias in grupos.items():
                for categoria, pdfs in categorias.items():
                    for pdf in pdfs:
                        if os.path.exists(pdf):
                            archivos_para_zip.append(Path(pdf))

    _report_progress(request, 80)

    total_archivos = max(len(archivos_para_zip), 1)
    procesados = 0

    with zipfile.ZipFile(
        final_zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=4,
    ) as zipf:
        for archivo in archivos_para_zip:
            if archivo == main_pdf_path:
                nombre_zip = "Reporte_Principal.pdf"
            else:
                nombre_zip = f"anexos/{archivo.name}"

            zipf.write(archivo, nombre_zip)

            procesados += 1
            progreso_local = procesados / total_archivos
            _report_progress(request, 80 + int(15 * progreso_local))

    try:
        if delivery_dir.exists():
            shutil.rmtree(delivery_dir)

        if tmp_collector_pdf.exists():
            tmp_collector_pdf.unlink()

        if tmp_main_pdf.exists():
            tmp_main_pdf.unlink()

        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    except Exception as exc:
        print(f"No se pudo limpiar todo el temporal: {exc}")

    _report_progress(request, 100)

    return ReportGenerationResult(
        job_id=request.job_id,
        main_pdf_path=main_pdf_path,
        final_zip_path=final_zip_path,
        success=True,
    )