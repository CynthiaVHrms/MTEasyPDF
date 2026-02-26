import zipfile
import os
import re
import sys
import shutil
import unicodedata
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from collections import defaultdict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from pdf_utils import (
    draw_images,
    draw_images_by_rows,
    build_pdf_tree,
    MARGIN,
    TOP_SAFE_MARGIN,
)

from pdf_layout import (
    draw_cover,
    draw_header_footer,
    draw_section_title,
    draw_subsection_title,
    nueva_pagina_con_titulo,
    draw_index,
    draw_introduccion,
    render_documentacion_links,
)

from file_engine import (
    limpiar_temp,
    extraer_zip,
    obtener_carpeta_raiz,
    clasificar_archivos,
    build_mantenimiento_tree,
    agrupar_pdfs_por_categoria,
    calcular_paginas_indice,
)

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_PATH = "ejemplo.zip"
TEMP_DIR = "temp"
project_data = {}
PAGE_WIDTH, PAGE_HEIGHT = A4
TEXT_HEIGHT = 14
TITLE_HEIGHT = 22
MIN_SPACE_AFTER_TITLE = 150

try:
    pdfmetrics.registerFont(TTFont("Arial", "arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", "arialbd.ttf"))
    FUENTE_TEXTO = "Arial"
    FUENTE_NEGRITA = "Arial-Bold"
except:
    # Si falla (ej. en Linux), regresamos a la estándar
    FUENTE_TEXTO = "Helvetica"
    FUENTE_NEGRITA = "Helvetica-Bold"


# ============================================================
# FILE UTILS
# ============================================================
class IndexCollector:
    def __init__(self):
        self.items = []

    def add(self, title, page, level=1):
        self.items.append({"title": title, "page": page, "level": level})

    def get_items(self):
        return self.items


# ============================================================
# DATA CLASIFICATION
# ============================================================


def calcular_alto_imagenes(num_imagenes, layout):
    if layout == 4:
        imgs_por_fila = 4
        max_h = 220
    else:
        imgs_por_fila = 2
        max_h = 250

    filas = (num_imagenes + imgs_por_fila - 1) // imgs_por_fila

    row_gap = max_h + TEXT_HEIGHT + 48
    top_padding = 10
    bottom_padding = 20

    return top_padding + (filas * row_gap) + bottom_padding


def render_mantenimiento(
    canvas,
    cursor_y,
    tree,
    pdf_tree,
    project_data,
    index=None,
    insert_tasks=None,
    usa_ubicacion=True,
    callback_progreso=None,
):
    MIN_BOTTOM = 120
    TITLE_GAP = 2
    imagenes_procesadas_ref = [0]
    print("🔥 render_mantenimiento ejecutándose")

    # ---- CONTAR TOTAL DE IMÁGENES ----
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

    imagenes_procesadas = 0

    for i_sec, (seccion, subsecciones) in enumerate(tree.items()):
        # Nueva sección siempre hoja nueva (ya lo hace tu función)
        cursor_y = nueva_pagina_con_titulo(canvas, project_data, seccion)
        if index:
            index.add(seccion, canvas.getPageNumber(), level=1)

        for i_sub, (subseccion, grupos) in enumerate(subsecciones.items()):
            # --- REGLA: SALTO EN SUBSECCIÓN ---
            if usa_ubicacion and i_sub > 0:
                canvas.showPage()
                draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                cursor_y = draw_section_title(canvas, seccion, TOP_SAFE_MARGIN)

            if subseccion != "__SIN_UBICACION__" and usa_ubicacion:
                cursor_y = draw_subsection_title(canvas, subseccion, cursor_y)
                if index:
                    index.add(subseccion, canvas.getPageNumber(), level=2)

            for i_gru, (grupo, categorias) in enumerate(grupos.items()):
                # --- REGLA: SALTO EN GRUPO (solo si no hay ubicación) ---
                if not usa_ubicacion:
                    if not (i_sub == 0 and i_gru == 0):
                        canvas.showPage()
                        draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                        cursor_y = draw_section_title(canvas, seccion, TOP_SAFE_MARGIN)

                if cursor_y < (MIN_BOTTOM + TITLE_HEIGHT + MIN_SPACE_AFTER_TITLE):
                    canvas.showPage()
                    draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                    cursor_y = draw_section_title(canvas, seccion, TOP_SAFE_MARGIN)

                if grupo:
                    cursor_y = draw_subsection_title(canvas, grupo, cursor_y)
                    if index:
                        index.add(grupo, canvas.getPageNumber(), level=3)

                for i_cat, (categoria, imagenes_nativas) in enumerate(
                    categorias.items()
                ):
                    imgs_cat = [
                        f
                        for f in imagenes_nativas
                        if f.lower().endswith((".jpg", ".jpeg", ".png"))
                    ]
                    if not imgs_cat:
                        continue

                    if categoria:
                        # --- DETECCIÓN DE LAYOUT ---
                        niveles_texto = [
                            str(seccion),
                            str(subseccion),
                            str(grupo),
                            str(categoria),
                        ]
                        txt_busqueda = " ".join(niveles_texto).lower()

                        is_full_width = (
                            "pantalla" in txt_busqueda or "pruebas" in txt_busqueda
                        )

                        if is_full_width:
                            max_h = 240
                        else:
                            max_h = 220

                        row_gap = max_h + TEXT_HEIGHT + 30
                        bottom_limit = 80  # MISMO que draw_images_by_rows

                        altura_necesaria = 22 + row_gap  # título + una fila real

                        if cursor_y - altura_necesaria < bottom_limit:
                            canvas.showPage()
                            draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                            cursor_y = draw_section_title(canvas, seccion, TOP_SAFE_MARGIN)

                        cursor_y = draw_subsection_title(canvas, categoria, cursor_y)

                    # --- DETECCIÓN DE LAYOUT ---
                    niveles_texto = [
                        str(seccion),
                        str(subseccion),
                        str(grupo),
                        str(categoria),
                    ]
                    txt_busqueda = " ".join(niveles_texto).lower()

                    # Regla de negocio: pantalla/pruebas = 1 foto por fila, mantenimiento = 2.
                    is_full_width = (
                        "pantalla" in txt_busqueda or "pruebas" in txt_busqueda
                    )
                    num_fotos_fila = 1 if is_full_width else 2

                    # --- LLAMADA A TU NUEVA FUNCIÓN ---
                    cursor_y = draw_images_by_rows(
                        canvas,
                        imgs_cat,
                        images_per_row=num_fotos_fila,
                        start_y=cursor_y,
                        project_data=project_data,  # Para que sepa redibujar header
                        seccion=seccion,  # Para que sepa redibujar título
                        callback_progreso=callback_progreso,
                        total_imagenes=total_imagenes,
                        imagenes_procesadas_ref=imagenes_procesadas_ref,
                    )

    return cursor_y


def build_pdf(
    filename,
    with_index,
    data,
    mantenimiento_tree,
    index_items=None,
    index=None,
    usa_ubicacion=True,
):
    # pageCompression=1 es genial para que no pese tanto
    c = canvas.Canvas(filename, pagesize=A4, pageCompression=1)

    # Solo necesitamos rastrear el cursor vertical, el número lo lleva el canvas
    cursor_y = TOP_SAFE_MARGIN

    # -------- PORTADA --------
    # draw_cover internamente ya llama a draw_header_footer con None (sin número)
    draw_cover(
        c,
        {
            "titulo": project_data["titulo"],
            "info_extra": project_data["info_extra"],
            "imagen_portada": project_data["imagen_portada"],
        },
        project_data,
    )

    # -------- INTRODUCCIÓN --------
    # Al salir de draw_cover ya hubo un showPage(), así que aquí estamos en la pág 2
    draw_header_footer(c, c.getPageNumber(), project_data)
    # Importante: draw_introduccion ahora recibe project_data para sus propios saltos
    cursor_y = draw_introduccion(c, project_data["introduccion"], project_data)

    # Preparamos para lo que sigue (Ubicación o Índice)
    c.showPage()

    # -------- ÍNDICE (solo si ya existe) --------
    if with_index and index_items:
        draw_header_footer(c, c.getPageNumber(), project_data)
        # Eliminamos start_page, el layout ahora usa getPageNumber()
        draw_index(c, index_items, project_data)
        # draw_index ya termina con un showPage() interno

    # -------- UBICACIÓN --------
    if usa_ubicacion and data.get("ubicacion"):
        imagenes_restantes = data["ubicacion"][:]

        while imagenes_restantes:
            # Dibujamos encabezado de la página actual de ubicación
            draw_header_footer(c, c.getPageNumber(), project_data)

            cursor_y = draw_section_title(c, "Ubicación")
            cursor_y -= 20

            # Si quieres que la ubicación aparezca en el índice:
            if index:
                index.add("Ubicación", c.getPageNumber(), level=1)

            imagenes_restantes, used_height = draw_images(
                c,
                imagenes_restantes,
                per_page=2,
                start_y=cursor_y,
            )

            cursor_y -= used_height

            # Si quedan más imágenes de ubicación, saltamos de página
            if imagenes_restantes:
                c.showPage()
                cursor_y = TOP_SAFE_MARGIN

    # -------- MANTENIMIENTO --------
    # MODIFICADO: Solo enviamos y recibimos cursor_y
    cursor_y = render_mantenimiento(
        c,
        cursor_y,
        mantenimiento_tree,
        project_data,
        index=index,
    )

    c.save()


# ============================================================
# MAIN
# ============================================================


def resource_path(relative_path):
    """Obtiene la ruta absoluta para recursos, funciona en dev y en PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def main(gui_data=None, callback_progreso=None):

    # ============================================================
    # PREPARACIÓN
    # ============================================================
    project_data = {}

    if gui_data:
        project_data.update(gui_data)
        ZIP_PATH = gui_data.get("zip_path")
        usa_ubicacion = gui_data.get("usa_ubicacion", True)

    # Validación estricta
    if not project_data.get("titulo") or not ZIP_PATH:
        raise ValueError("Error crítico: No se recibió información obligatoria.")

    def reportar(n):
        if callback_progreso:
            callback_progreso(n)

    reportar(10)  # 10% - Iniciando

    limpiar_temp(TEMP_DIR)
    extraer_zip(ZIP_PATH, TEMP_DIR)


    raiz = obtener_carpeta_raiz(TEMP_DIR)
    data = clasificar_archivos(raiz)

    mantenimiento_tree = build_mantenimiento_tree(
        data["mantenimiento"]["imagenes"], raiz, usa_ubicacion=usa_ubicacion
    )

    pdf_tree = build_pdf_tree(
        data["mantenimiento"]["pdfs"], raiz, usa_ubicacion=usa_ubicacion
    )

    pdfs_mantenimiento_tree = agrupar_pdfs_por_categoria(
        data["mantenimiento"]["pdfs"], raiz, usa_ubicacion=usa_ubicacion
    )

    insert_tasks = []

    destino_base = gui_data.get("output_dir", "output") if gui_data else "output"

    # ============================================================
    # PRIMERA PASADA (Solo para recolectar el Índice)
    # ============================================================
    index = IndexCollector()

    if not os.path.exists("output"):
        os.makedirs("output")

    # Archivo temporal para medir distancias y páginas
    c = canvas.Canvas("output/_tmp_recolector.pdf", pagesize=A4)
    cursor_y = TOP_SAFE_MARGIN

    # ---------------- PORTADA ----------------
    draw_cover(c, project_data, project_data)
    # Al salir de draw_cover, el canvas ya hizo un showPage() internamente

    # ---------------- INTRODUCCIÓN ----------------
    draw_header_footer(c, c.getPageNumber(), project_data)
    # Importante: enviamos project_data para que draw_introduccion gestione sus propios saltos
    cursor_y = draw_introduccion(c, project_data["introduccion"], project_data)
    c.showPage()

    # --- Simulación de espacio para el Índice ---
    num_paginas_idx = calcular_paginas_indice(
        mantenimiento_tree, data, usa_ubicacion=usa_ubicacion
    )
    for _ in range(num_paginas_idx):
        if usa_ubicacion:
            c.showPage()

    # ---------------- UBICACIÓN ----------------
    if usa_ubicacion and data.get("ubicacion"):
        index.add("Ubicación", c.getPageNumber(), level=1)
        imagenes_restantes = data["ubicacion"][:]

        while imagenes_restantes:
            draw_header_footer(c, c.getPageNumber(), project_data)
            cursor_y = draw_section_title(c, "Ubicación")
            cursor_y -= 20

            # Mantenemos tu lógica de 1 o 2 imágenes
            per_page = 1 if len(imagenes_restantes) == 1 else 2

            imagenes_restantes, used_height = draw_images(
                c,
                imagenes_restantes,
                per_page=per_page,
                start_y=cursor_y,
            )
            cursor_y -= used_height

            if imagenes_restantes:
                c.showPage()
                cursor_y = TOP_SAFE_MARGIN

    # ---------------- INVENTARIO ----------------
    if data["inventario"]:

        for pdf in data["inventario"]:
            # 1. Dibujamos la página del marcador (la que tendrá el encabezado)
            c.showPage()

            # Si es el primer PDF del inventario, registramos la sección
            if pdf == data["inventario"][0]:
                index.add("Inventario", c.getPageNumber(), level=1)

            # 2. SIMULACIÓN: Si el PDF tiene 5 páginas, el índice debe saltar 4 páginas más
            # para que la siguiente sección no empiece en un número falso.
            if os.path.exists(pdf):
                reader_temp = PdfReader(pdf)
                # Saltamos N-1 páginas porque la primera ya la creamos con showPage()
                for _ in range(len(reader_temp.pages) - 1):
                    c.showPage()

    # ---------------- MANTENIMIENTO ----------------
    # Esta es la función que limpiamos antes. Solo devuelve cursor_y.
    cursor_y = render_mantenimiento(
        c,
        PAGE_HEIGHT - 100,  # Iniciamos cursor arriba
        mantenimiento_tree,
        pdfs_mantenimiento_tree,
        project_data,
        index=index,  # Aquí se recolectan niveles 1, 2 y 3
        insert_tasks=None,  # En la primera pasada no necesitamos anotar tareas de reemplazo
        callback_progreso=None,
    )

    # --- DOCUMENTACIÓN TÉCNICA (links PDFs de mantenimiento) ---
    cursor_y = render_documentacion_links(
        c,
        PAGE_HEIGHT - 100,
        pdfs_mantenimiento_tree,  # <--- CAMBIAR pdf_tree POR pdfs_mantenimiento_tree
        project_data,
        index=index,
    )

    # ---------------- ANEXOS ----------------
    # Aseguramos que los Anexos empiecen en página nueva
    c.showPage()
    index.add("Anexos", c.getPageNumber(), level=1)

    # Opcional: puedes simular el listado de anexos si quieres que el índice sea ultra preciso
    # pero normalmente es solo una página.

    c.save()  # Guardamos para procesar el index.items

    index_items = index.get_items()

    # ============================================================
    # SEGUNDA PASADA (Generación del PDF con Diseño y Marcadores)
    # ============================================================
    insert_tasks = []  # Aquí anotamos: "En la página X, va el PDF Y"

    c = canvas.Canvas("output/mvp_imagenes.pdf", pagesize=A4, pageCompression=1)

    # ---------------- PORTADA ----------------
    draw_cover(c, project_data, project_data)

    # ---------------- INTRODUCCIÓN ----------------
    draw_header_footer(c, c.getPageNumber(), project_data)
    # Pasamos project_data para que draw_introduccion maneje sus propios saltos de página
    cursor_y = draw_introduccion(c, project_data["introduccion"], project_data)
    c.showPage()

    # ---------------- ÍNDICE ----------------
    # Ya no calculamos start_page, draw_index usa getPageNumber() internamente
    draw_header_footer(c, c.getPageNumber(), project_data)
    draw_index(c, index_items, project_data)
    # Al salir de draw_index ya se hizo un showPage()

    # ---------------- UBICACIÓN ----------------
    if usa_ubicacion and data.get("ubicacion"):
        imagenes_restantes = data["ubicacion"][:]
        while imagenes_restantes:
            draw_header_footer(c, c.getPageNumber(), project_data)
            cursor_y = draw_section_title(c, "Ubicación")
            cursor_y -= 20

            per_page = 1 if len(imagenes_restantes) == 1 else 2
            imagenes_restantes, used_height = draw_images(
                c, imagenes_restantes, per_page=per_page, start_y=cursor_y
            )

            if imagenes_restantes:
                c.showPage()

        c.showPage()  # Necesario para cuando se necesita más de una hoja

    # ---------------- INVENTARIO (Segunda Pasada) ----------------
    for i, pdf in enumerate(data["inventario"]):

        # 👉 A partir del segundo PDF, iniciamos página nueva
        if i > 0:
            c.showPage()

        p_actual = c.getPageNumber()
        draw_header_footer(c, p_actual, project_data)

        # Anotamos la página donde inicia el PDF real
        insert_tasks.append((p_actual, pdf))

        c.setFont(FUENTE_NEGRITA, 14)
        c.drawString(MARGIN, PAGE_HEIGHT - 120, f"Documento: {os.path.basename(pdf)}")

        # Simulamos las páginas restantes del PDF
        if os.path.exists(pdf):
            reader_temp = PdfReader(pdf)
            paginas_pdf = len(reader_temp.pages)

            for _ in range(paginas_pdf - 1):
                c.showPage()

    # ---------------- MANTENIMIENTO ----------------
    render_mantenimiento(
        c,
        PAGE_HEIGHT - 100,
        mantenimiento_tree,
        pdfs_mantenimiento_tree,
        project_data,
        index=None,  # Ya no recolectamos, ya tenemos index_items
        insert_tasks=insert_tasks,
        callback_progreso=callback_progreso,
    )

    # --- DOCUMENTACIÓN TÉCNICA (links PDFs de mantenimiento) ---
    cursor_y = render_documentacion_links(
        c,
        PAGE_HEIGHT - 100,
        pdfs_mantenimiento_tree,  # <--- CAMBIAR pdf_tree POR pdfs_mantenimiento_tree
        project_data,
        index=None,
    )

    # ---------------- ANEXOS (Listado con Links) ----------------
    c.showPage()
    draw_header_footer(c, c.getPageNumber(), project_data)

    cursor_y = draw_section_title(c, "Anexos del Proyecto", PAGE_HEIGHT - 100)
    cursor_y -= 20

    c.setFont(FUENTE_TEXTO, 12)
    for pdf in data["anexos"]:
        nombre = os.path.basename(pdf)
        c.setFillColor("blue")
        c.drawString(MARGIN + 20, cursor_y, f"• {nombre}")

        # El link es relativo a la carpeta donde estará el PDF final
        c.linkURL(
            f"anexos/{nombre}", (MARGIN + 20, cursor_y, MARGIN + 350, cursor_y + 12)
        )

        cursor_y -= 25
        if cursor_y < 120:
            c.showPage()
            draw_header_footer(c, c.getPageNumber(), project_data)
            cursor_y = PAGE_HEIGHT - 120

    c.save()

    print("Insertando archivos PDF y generando versión final...")

    # Abrimos el lector principal
    reader = PdfReader("output/mvp_imagenes.pdf")
    writer = PdfWriter()

    # Creamos el buscador de tareas (Página: Ruta_PDF)
    tareas_dict = {p[0]: p[1] for p in insert_tasks}

    # Mantenemos una lista de lectores para evitar cierres prematuros
    lectores_externos = []

    # --- VARIABLE CLAVE PARA ELIMINAR HOJAS EN BLANCO ---
    skip_until = -1

    for i, page in enumerate(reader.pages):
        num_pdf = i + 1

        # Si esta página es un "hueco" que creamos en el canvas, la saltamos
        if num_pdf <= skip_until:
            continue

        if num_pdf in tareas_dict:
            ruta_pdf_real = tareas_dict[num_pdf]
            if os.path.exists(ruta_pdf_real):
                print(
                    f"-> Insertando: {os.path.basename(ruta_pdf_real)} (Sustituye pág {num_pdf})"
                )

                ext_reader = PdfReader(ruta_pdf_real)
                lectores_externos.append(ext_reader)

                # Insertamos todas las páginas del PDF real
                for page_ext in ext_reader.pages:
                    writer.add_page(page_ext)

                # --- LÓGICA DE SALTO ---
                # Si el PDF real tiene 5 páginas y empezó en la 6,
                # el canvas generó la 7, 8, 9 y 10 como blancas.
                # Esta línea le dice al bucle que ignore esas páginas del reader.
                skip_until = num_pdf + len(ext_reader.pages) - 1

            else:
                print(
                    f"⚠️ Archivo no encontrado: {ruta_pdf_real}. Manteniendo marcador."
                )
                writer.add_page(page)
        else:
            # Página normal (Introducción, Ubicación, Mantenimiento, etc.)
            writer.add_page(page)

    # Aseguramos que la carpeta base exista
    if not os.path.exists(destino_base):
        os.makedirs(destino_base)

    # --- PREPARACIÓN DE CARPETAS ---
    # Extraemos la ruta que eligió el usuario en la GUI
    ruta_destino_usuario = (
        gui_data.get("output_dir", "output") if gui_data else "output"
    )

    # Construimos las rutas finales en esa carpeta
    entrega_dir = os.path.join(ruta_destino_usuario, "Reporte_Final_Entrega")
    zip_entrega = os.path.join(ruta_destino_usuario, "Memoria_Tecnica_Final.zip")
    anexos_dir = os.path.join(entrega_dir, "anexos")

    if os.path.exists(entrega_dir):
        shutil.rmtree(entrega_dir)
    os.makedirs(anexos_dir)

    # --- ESCRITURA FINAL ---
    output_path = os.path.join(entrega_dir, "Reporte_Principal.pdf")

    # Copiamos metadatos básicos
    if reader.metadata:
        writer.add_metadata(reader.metadata)

    with open(output_path, "wb") as f:
        writer.write(f)

    # Contar archivos para barra de progreso
    archivos_para_zip = []

    # PDF principal
    archivos_para_zip.append(output_path)

    # Anexos directos
    for pdf_anexo in data.get("anexos", []):
        if os.path.exists(pdf_anexo):
            archivos_para_zip.append(pdf_anexo)

    # PDFs del árbol
    for seccion, subsecciones in pdf_tree.items():
        for subseccion, grupos in subsecciones.items():
            for grupo, categorias in grupos.items():
                for categoria, pdfs in categorias.items():
                    for pdf in pdfs:
                        if os.path.exists(pdf):
                            archivos_para_zip.append(pdf)

    total_archivos = len(archivos_para_zip)
    procesados = 0

    # --- COPIAR ANEXOS EXTERNOS ---
    reportar(80)  # empieza la compresión

    with zipfile.ZipFile(
        zip_entrega, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=4
    ) as zipf:

        for archivo in archivos_para_zip:

            # Determinar nombre dentro del ZIP
            if archivo == output_path:
                nombre_zip = "Reporte_Principal.pdf"
            else:
                nombre_zip = f"anexos/{os.path.basename(archivo)}"

            zipf.write(archivo, nombre_zip)

            # 🔥 Actualizar progreso
            procesados += 1
            progreso_local = procesados / total_archivos
            reportar(80 + int(15 * progreso_local))

    # --- BLOQUE DE LIMPIEZA FINAL OPTIMIZADO ---
    try:
        # 1. Borrar la carpeta de trabajo donde se armó el reporte
        if os.path.exists(entrega_dir):
            shutil.rmtree(entrega_dir)

        # 2. Borrar la carpeta temp (donde se extrajo el ZIP original)
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)

        # 3. Borrar archivos PDF intermedios que ya están dentro del ZIP final
        archivos_a_limpiar = ["output/_tmp_recolector.pdf", "output/mvp_imagenes.pdf"]
        for archivo in archivos_a_limpiar:
            if os.path.exists(archivo):
                os.remove(archivo)

        print(f"🧹 Limpieza profunda completada. Solo queda el ZIP de entrega.")
    except Exception as e:
        print(f"⚠️ Nota: Algunos archivos temporales no pudieron borrarse: {e}")

    reportar(100)  # Indica a la interfaz que terminamos
    return zip_entrega

    print(f"✅ Proceso completo. Carpeta generada en: {entrega_dir}")


if __name__ == "__main__":
    main()
