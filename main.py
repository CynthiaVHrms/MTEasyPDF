import zipfile
import os
import shutil
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
from collections import defaultdict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from pdf_utils import (
    draw_images,
    MARGIN,
)

from pdf_layout import (
    draw_cover,
    draw_header_footer,
    draw_section_title,
    draw_subsection_title,
    nueva_pagina_con_titulo,
    draw_index,
    draw_introduccion,
)

from file_engine import (
    limpiar_temp,
    extraer_zip,
    obtener_carpeta_raiz,
    clasificar_archivos,
    build_mantenimiento_tree,
    agrupar_pdfs_por_categoria,
    calcular_paginas_indice,
    limpiar_nombre,
    obtener_niveles,
)

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_PATH = "ejemplo.zip"
TEMP_DIR = "temp"

PAGE_WIDTH, PAGE_HEIGHT = A4

project_data = {
    "titulo": "Reporte de Evidencias",
    "info_extra": "Proyecto MT - Marzo 2025",
    "introduccion": "Este documento contiene las evidencias recopiladas durante el proyecto MT.",
    "imagen_portada": os.path.join(BASE_DIR, "input", "portada.jpeg"),
    "logo_sup_izq": os.path.join(BASE_DIR, "input", "Cathi.png"),
    "logo_sup_der": os.path.join(BASE_DIR, "input", "Sari.png"),
    "logo_inf_izq": os.path.join(BASE_DIR, "input", "Dinamics.png"),
    "logo_inf_der": os.path.join(BASE_DIR, "input", "logo1.png"),
}


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


def imprimir_resumen(data):
    print("\n📍 Ubicación:", len(data["ubicacion"]), "imágenes")
    print("📊 Inventario:", len(data["inventario"]), "archivo(s)")
    print("🛠️ Mantenimiento:")
    print("   - imágenes:", len(data["mantenimiento"]["imagenes"]))
    print("   - pdfs:", len(data["mantenimiento"]["pdfs"]))
    print("📎 Anexos:", len(data["anexos"]), "pdf(s)")


def render_mantenimiento(
    canvas,
    cursor_y,
    tree,
    pdf_tree,
    project_data,
    index=None,
    insert_tasks=None,
):

    MIN_BOTTOM = 120  # margen seguro abajo (logos + número + aire)
    TITLE_GAP = 2  # espacio extra después de cada título/subtítulo

    for seccion, subsecciones in tree.items():

        cursor_y = nueva_pagina_con_titulo(
            canvas, project_data, seccion
        )
        if index:
            index.add(seccion, canvas.getPageNumber(), level=1)

        cursor_y -= TITLE_GAP  # ✅ separación real tras título de sección

        for subseccion, grupos in subsecciones.items():
            if subseccion:
                # si no cabe el subtítulo, nueva página
                if cursor_y < (MIN_BOTTOM + 40):
                    canvas.showPage()
                    draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                    cursor_y = PAGE_HEIGHT - 100
                    cursor_y = draw_section_title(canvas, seccion, cursor_y)

                cursor_y = draw_subsection_title(canvas, subseccion, cursor_y)
                if index:
                    index.add(subseccion, canvas.getPageNumber(), level=2)

                cursor_y -= TITLE_GAP

            for grupo, categorias in grupos.items():
                if grupo:
                    if cursor_y < (MIN_BOTTOM + 40):
                        canvas.showPage()
                        draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                        cursor_y = PAGE_HEIGHT - 100
                        cursor_y = draw_section_title(canvas, seccion, cursor_y)

                    cursor_y = draw_subsection_title(canvas, grupo, cursor_y)
                    if index:
                        index.add(grupo, canvas.getPageNumber(), level=3)

                    cursor_y -= TITLE_GAP

                contenido_dibujado = False

                for categoria, imagenes in categorias.items():
                    imagenes_categoria = []
                    pdfs_categoria = []

                    for archivo in imagenes:
                        if archivo.lower().endswith((".jpg", ".jpeg", ".png")):
                            imagenes_categoria.append(archivo)
                        elif archivo.lower().endswith(".pdf"):
                            pdfs_categoria.append(archivo)

                    # Si viene título de categoría, asegúrate que quepa antes de dibujarlo
                    if categoria:
                        if cursor_y < (MIN_BOTTOM + 40):
                            canvas.showPage()
                            draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                            cursor_y = PAGE_HEIGHT - 100
                            cursor_y = draw_section_title(canvas, seccion, cursor_y)

                        cursor_y = draw_subsection_title(
                            canvas, categoria, cursor_y
                        )  # ✅ usa retorno
                        cursor_y -= TITLE_GAP

                    nombre = (categoria or "").lower()
                    layout = 2 if ("pantalla" in nombre or "pruebas" in nombre) else 4
                    imagenes = imagenes_categoria

                    # Dibuja bloques de imágenes
                    while imagenes:
                        #  si no hay espacio suficiente, nueva página (antes de dibujar)
                        if cursor_y < (MIN_BOTTOM + 250):
                            canvas.showPage()
                            draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                            cursor_y = PAGE_HEIGHT - 100
                            cursor_y = draw_section_title(canvas, seccion, cursor_y)

                        imagenes, used_height = draw_images(
                            canvas,
                            imagenes,
                            per_page=layout,
                            start_y=cursor_y,
                        )

                        cursor_y -= used_height
                        contenido_dibujado = True


                    if contenido_dibujado and cursor_y < (PAGE_HEIGHT - 150):

                        canvas.showPage()
                        draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                        cursor_y = PAGE_HEIGHT - 100
                        cursor_y = draw_section_title(canvas, seccion, cursor_y)


                    pdf_de_esta_cat = (
                        pdf_tree.get(seccion, {})
                        .get(subseccion, {})
                        .get(grupo, {})
                        .get(categoria, [])
                    )

                    for pdf in pdf_de_esta_cat:
                        # Dentro de render_mantenimiento en main.py:
                        canvas.showPage()
                        actual_p = (
                            canvas.getPageNumber()
                        )  # Obtener página real del canvas
                        draw_header_footer(canvas, actual_p, project_data)

                        if insert_tasks is not None:
                            # Usamos la página real entregada por ReportLab
                            insert_tasks.append((actual_p, pdf))

                        canvas.getPageNumber == actual_p  # Sincronizar contador

                        # Dibujamos la carátula/marcador
                        cursor_y = PAGE_HEIGHT - 120
                        cursor_y = draw_section_title(
                            canvas, "Documentación Anexa", cursor_y
                        )

                        canvas.setFont("Helvetica", 11)
                        canvas.drawString(
                            MARGIN, cursor_y, f"Archivo: {os.path.basename(pdf)}"
                        )

                        contenido_dibujado = True

                    pdfs_categoria = (
                        pdf_tree.get(seccion, {})
                        .get(subseccion, {})
                        .get(grupo, {})
                        .get(categoria, [])
                    )

                    for pdf in pdfs_categoria:
                        canvas.showPage()
                        draw_header_footer(canvas, canvas.getPageNumber(), project_data)

                        cursor_y = PAGE_HEIGHT - 120
                        cursor_y = draw_section_title(canvas, "Documentación", cursor_y)

                        canvas.setFont("Helvetica", 11)
                        canvas.drawString(MARGIN, cursor_y, os.path.basename(pdf))

    return cursor_y


def build_pdf(
    filename, with_index, data, mantenimiento_tree, index_items=None, index=None
):
    # pageCompression=1 es genial para que no pese tanto
    c = canvas.Canvas(filename, pagesize=A4, pageCompression=1)

    # Solo necesitamos rastrear el cursor vertical, el número lo lleva el canvas
    cursor_y = PAGE_HEIGHT - 100

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
            cursor_y = PAGE_HEIGHT - 100

    # -------- MANTENIMIENTO --------
    # MODIFICADO: Solo enviamos y recibimos cursor_y
    cursor_y = render_mantenimiento(
        c, cursor_y, mantenimiento_tree, project_data, index=index
    )

    c.save()


# ============================================================
# MAIN
# ============================================================


def main():

    # ============================================================
    # PREPARACIÓN
    # ============================================================

    limpiar_temp(TEMP_DIR)
    extraer_zip(ZIP_PATH, TEMP_DIR)

    raiz = obtener_carpeta_raiz(TEMP_DIR)
    data = clasificar_archivos(raiz)

    mantenimiento_tree = build_mantenimiento_tree(
        data["mantenimiento"]["imagenes"], raiz
    )

    pdfs_mantenimiento_tree = agrupar_pdfs_por_categoria(
        data["mantenimiento"]["pdfs"], raiz
    )

    insert_tasks = []

    # ============================================================
    # PRIMERA PASADA (Solo para recolectar el Índice)
    # ============================================================
    index = IndexCollector()

    # Archivo temporal para medir distancias y páginas
    c = canvas.Canvas("output/_tmp_recolector.pdf", pagesize=A4)
    cursor_y = PAGE_HEIGHT - 100

    # ---------------- PORTADA ----------------
    draw_cover(c, project_data, project_data)
    # Al salir de draw_cover, el canvas ya hizo un showPage() internamente

    # ---------------- INTRODUCCIÓN ----------------
    draw_header_footer(c, c.getPageNumber(), project_data)
    # Importante: enviamos project_data para que draw_introduccion gestione sus propios saltos
    cursor_y = draw_introduccion(c, project_data["introduccion"], project_data)
    c.showPage()
    
    # --- Simulación de espacio para el Índice ---
    num_paginas_idx = calcular_paginas_indice(mantenimiento_tree, data)
    for _ in range(num_paginas_idx):
        c.showPage()

    # ---------------- UBICACIÓN ----------------
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
            cursor_y = PAGE_HEIGHT - 100


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

    # ---------------- INVENTARIO (Segunda Pasada) ----------------
    for pdf in data["inventario"]:
        c.showPage()
        p_actual = c.getPageNumber()
        draw_header_footer(c, p_actual, project_data)

        # Anotamos la página donde inicia el PDF
        insert_tasks.append((p_actual, pdf))

        c.setFont("Helvetica-Bold", 14)
        c.drawString(MARGIN, PAGE_HEIGHT - 120, f"Documento: {os.path.basename(pdf)}")

        # Avanzamos el contador para que la pág 10 sea realmente la 10
        if os.path.exists(pdf):
            reader_temp = PdfReader(pdf)
            paginas_pdf = len(reader_temp.pages)

            # Si el PDF tiene más de 1 página, creamos "huecos" en el canvas
            for _ in range(paginas_pdf - 1):
                c.showPage()
                # Opcional: anotar que esta página es de relleno
                # (aunque la lógica del writer que pondremos abajo lo detectará solo)

    # ---------------- MANTENIMIENTO ----------------
    render_mantenimiento(
        c,
        PAGE_HEIGHT - 100,
        mantenimiento_tree,
        pdfs_mantenimiento_tree,
        project_data,
        index=None,  # Ya no recolectamos, ya tenemos index_items
        insert_tasks=insert_tasks,
    )

    # ---------------- ANEXOS (Listado con Links) ----------------
    c.showPage()
    draw_header_footer(c, c.getPageNumber(), project_data)

    cursor_y = draw_section_title(c, "Anexos del Proyecto", PAGE_HEIGHT - 120)
    cursor_y -= 20

    c.setFont("Helvetica", 12)
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
                print(f"-> Insertando: {os.path.basename(ruta_pdf_real)} (Sustituye pág {num_pdf})")

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
                print(f"⚠️ Archivo no encontrado: {ruta_pdf_real}. Manteniendo marcador.")
                writer.add_page(page)
        else:
            # Página normal (Introducción, Ubicación, Mantenimiento, etc.)
            writer.add_page(page)

    # --- PREPARACIÓN DE CARPETAS ---
    entrega_dir = "output/Reporte_Final_Entrega"
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

    # --- COPIAR ANEXOS EXTERNOS ---
    for pdf_anexo in data.get("anexos", []):
        if os.path.exists(pdf_anexo):
            shutil.copy(pdf_anexo, anexos_dir)

    print(f"✅ Proceso completo. Carpeta generada en: {entrega_dir}")


if __name__ == "__main__":
    main()
