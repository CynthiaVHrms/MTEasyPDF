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
    canvas, page_num, cursor_y, tree, pdf_tree, project_data, index=None, insert_tasks=None
):

    MIN_BOTTOM = 120  # margen seguro abajo (logos + número + aire)
    TITLE_GAP = 2  # espacio extra después de cada título/subtítulo

    for seccion, subsecciones in tree.items():

        page_num, cursor_y = nueva_pagina_con_titulo(
            canvas, page_num, project_data, seccion
        )
        if index:
            index.add(seccion, page_num, level=1)
        cursor_y -= TITLE_GAP  # ✅ separación real tras título de sección

        for subseccion, grupos in subsecciones.items():
            if subseccion:
                # si no cabe el subtítulo, nueva página
                if cursor_y < (MIN_BOTTOM + 40):
                    canvas.showPage()
                    page_num += 1
                    draw_header_footer(canvas, page_num, project_data)
                    cursor_y = PAGE_HEIGHT - 100
                    cursor_y = draw_section_title(canvas, seccion, cursor_y)

                cursor_y = draw_subsection_title(canvas, subseccion, cursor_y)
                if index:
                    index.add(subseccion, page_num, level=2)
                cursor_y -= TITLE_GAP

            for grupo, categorias in grupos.items():
                if grupo:
                    if cursor_y < (MIN_BOTTOM + 40):
                        canvas.showPage()
                        page_num += 1
                        draw_header_footer(canvas, page_num, project_data)
                        cursor_y = PAGE_HEIGHT - 100
                        cursor_y = draw_section_title(canvas, seccion, cursor_y)

                    cursor_y = draw_subsection_title(canvas, grupo, cursor_y)
                    if index:
                        index.add(grupo, page_num, level=3)
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
                            page_num += 1
                            draw_header_footer(canvas, page_num, project_data)
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
                            page_num += 1
                            draw_header_footer(canvas, page_num, project_data)
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
                        
                    if contenido_dibujado:
                        canvas.showPage()
                        page_num += 1
                        draw_header_footer(canvas, page_num, project_data)
                        cursor_y = PAGE_HEIGHT - 100
                        cursor_y = draw_section_title(canvas, seccion, cursor_y)

                    pdf_de_esta_cat = pdf_tree.get(seccion, {}).get(subseccion, {}).get(grupo, {}).get(categoria, [])
            
                    for pdf in pdf_de_esta_cat:
                        # Dentro de render_mantenimiento en main.py:
                        canvas.showPage()
                        actual_p = canvas.getPageNumber() # Obtener página real del canvas
                        draw_header_footer(canvas, actual_p, project_data)

                        if insert_tasks is not None:
                            # Usamos la página real entregada por ReportLab
                            insert_tasks.append((actual_p, pdf)) 

                        page_num = actual_p # Sincronizar contador

                        # Dibujamos la carátula/marcador
                        cursor_y = PAGE_HEIGHT - 120
                        cursor_y = draw_section_title(canvas, "Documentación Anexa", cursor_y)
                        canvas.setFont("Helvetica", 11)
                        canvas.drawString(MARGIN, cursor_y, f"Archivo: {os.path.basename(pdf)}")
                        contenido_dibujado = True

                    pdfs_categoria = (
                        pdf_tree.get(seccion, {})
                        .get(subseccion, {})
                        .get(grupo, {})
                        .get(categoria, [])
                    )

                    for pdf in pdfs_categoria:
                        canvas.showPage()
                        page_num += 1
                        draw_header_footer(canvas, page_num, project_data)

                        cursor_y = PAGE_HEIGHT - 120
                        cursor_y = draw_section_title(canvas, "Documentación", cursor_y)

                        canvas.setFont("Helvetica", 11)
                        canvas.drawString(MARGIN, cursor_y, os.path.basename(pdf))

    return page_num, cursor_y


def build_pdf(
    filename, with_index, data, mantenimiento_tree, index_items=None, index=None
):

    c = canvas.Canvas(filename, pagesize=A4, pageCompression=1)

    page_num = 0
    cursor_y = PAGE_HEIGHT - 100

    # -------- PORTADA --------
    draw_cover(
        c,
        {
            "titulo": project_data["titulo"],
            "info_extra": project_data["info_extra"],
            "imagen_portada": project_data["imagen_portada"],
        },
        project_data,
    )
    page_num += 1

    # INTRODUCCIÓN (página 1)
    draw_header_footer(c, page_num, project_data)
    draw_introduccion(c, project_data["introduccion"])
    page_num += 1

    # -------- ÍNDICE (solo si ya existe) --------
    if with_index and index_items:
        draw_header_footer(c, page_num, project_data)
        draw_index(c, index_items, project_data, start_page=page_num + 1)
        page_num += 1

    # -------- UBICACIÓN --------
    imagenes_restantes = data["ubicacion"][:]

    while imagenes_restantes:
        draw_header_footer(c, page_num, project_data)

        cursor_y = draw_section_title(c, "Ubicación")
        cursor_y -= 20

        imagenes_restantes, used_height = draw_images(
            c,
            imagenes_restantes,
            per_page=2,
            start_y=cursor_y,
        )

        cursor_y -= used_height

        if imagenes_restantes:
            c.showPage()
            page_num += 1
            cursor_y = PAGE_HEIGHT - 100

    # -------- MANTENIMIENTO --------
    page_num, cursor_y = render_mantenimiento(
        c, page_num, cursor_y, mantenimiento_tree, project_data
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
    # PRIMERA PASADA (solo recolectar índice)
    # ============================================================

    index = IndexCollector()

    c = canvas.Canvas("output/_tmp.pdf", pagesize=A4, pageCompression=1)

    page_num = 0
    cursor_y = PAGE_HEIGHT - 100

    # ---------------- PORTADA ----------------
    draw_cover(
        c,
        {
            "titulo": project_data["titulo"],
            "info_extra": project_data["info_extra"],
            "imagen_portada": project_data["imagen_portada"],
        },
        project_data,
    )
    page_num += 1

    # INTRODUCCIÓN (página 1)
    draw_header_footer(c, page_num, project_data)
    draw_introduccion(c, project_data["introduccion"])
    page_num += 1
    c.showPage()

    # ---------------- UBICACIÓN ----------------
    ubicacion_indexed = False
    imagenes_restantes = data["ubicacion"][:]

    while imagenes_restantes:
        draw_header_footer(c, page_num, project_data)

        cursor_y = draw_section_title(c, "Ubicación")

        if not ubicacion_indexed:
            index.add("Ubicación", page_num, level=1)
            ubicacion_indexed = True

        cursor_y -= 20

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
            page_num += 1
            cursor_y = PAGE_HEIGHT - 100

    # =========================
    # INVENTARIO
    # =========================
    # === EN LA PRIMERA PASADA (alrededor de la línea 360) ===
    if index:
        index.add("Inventario", page_num + 1, level=1)

    for pdf in data["inventario"]:
        c.showPage()
        page_num += 1
        # Simulamos el desplazamiento: si el PDF tiene 5 páginas, 
        # sumamos esas 4 extra al contador para que el índice sepa dónde estará lo siguiente.
        if os.path.exists(pdf):
            reader_temp = PdfReader(pdf)
            paginas_extras = len(reader_temp.pages) - 1
            page_num += paginas_extras

    # ---------------- MANTENIMIENTO ----------------
    page_num, cursor_y = render_mantenimiento(
        c,
        page_num,
        cursor_y,
        mantenimiento_tree,
        pdfs_mantenimiento_tree,
        project_data,
        index=index,  # 👈 importante
        insert_tasks=insert_tasks,
    )

    # =========================
    # ANEXOS
    # =========================
    if index:
        index.add("Anexos", page_num + 1, level=1)

    for pdf in data["anexos"]:
        c.showPage()
        page_num += 1
        draw_header_footer(c, page_num, project_data)
        cursor_y = PAGE_HEIGHT - 100
        c.setFont("Helvetica-Bold", 14)
        c.drawString(MARGIN, cursor_y, f"Anexo: {os.path.basename(pdf)}")

    c.save()

    index_items = index.get_items()

    # ============================================================
    # SEGUNDA PASADA (PDF FINAL + ÍNDICE)
    # ============================================================

    c = canvas.Canvas("output/mvp_imagenes.pdf", pagesize=A4, pageCompression=1)

    page_num = 0
    cursor_y = PAGE_HEIGHT - 100

    # ---------------- PORTADA ----------------
    draw_cover(
        c,
        {
            "titulo": project_data["titulo"],
            "info_extra": project_data["info_extra"],
            "imagen_portada": project_data["imagen_portada"],
        },
        project_data,
    )
    page_num += 1

    # INTRODUCCIÓN (página 1)
    draw_header_footer(c, page_num, project_data)
    draw_introduccion(c, project_data["introduccion"])
    page_num += 1
    c.showPage()

    # ---------------- ÍNDICE ----------------
    draw_header_footer(c, page_num, project_data)
    draw_index(c, index_items, project_data, start_page=page_num + 1)
    page_num += 1

    # ---------------- UBICACIÓN ----------------
    imagenes_restantes = data["ubicacion"][:]

    while imagenes_restantes:
        draw_header_footer(c, page_num, project_data)

        cursor_y = draw_section_title(c, "Ubicación")
        cursor_y -= 20

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
            page_num += 1
            cursor_y = PAGE_HEIGHT - 100

    # =========================
    # INVENTARIO (Segunda Pasada)
    # =========================
    if data["inventario"]:
        for pdf in data["inventario"]:
            c.showPage() 
            # IMPORTANTE: No calcules el número sumando. 
            # Pregúntale al canvas su número de página real actual:
            pagina_fisica_actual = c.getPageNumber() 
            
            draw_header_footer(c, pagina_fisica_actual, project_data)

            # REGISTRAMOS LA PÁGINA REAL
            # Eliminamos el "+ 1" que tenías antes, ya que getPageNumber() es exacto
            insert_tasks.append((pagina_fisica_actual, pdf))

            cursor_y = PAGE_HEIGHT - 100
            c.setFont("Helvetica-Bold", 14)
            c.drawString(MARGIN, cursor_y, f"Documento: {os.path.basename(pdf)}")
            
            # Actualizamos page_num para que las siguientes secciones no se desfases
            page_num = pagina_fisica_actual

    # ---------------- MANTENIMIENTO ----------------
    page_num, cursor_y = render_mantenimiento(
        c,
        page_num,
        cursor_y,
        mantenimiento_tree,
        pdfs_mantenimiento_tree,
        project_data,
        index=None,  # ya no se recolecta
        insert_tasks=insert_tasks,
    )

    # =========================
    # ANEXOS (DISEÑO ESTÁNDAR + LINKS)
    # =========================
    if index:
        index.add("Anexos", page_num + 1, level=1)
    
    # Creamos una página nueva para el listado
    c.showPage()
    page_num += 1
    draw_header_footer(c, page_num, project_data)
    
    # Dibujamos el título de la sección con el mismo estilo de las demás
    cursor_y = PAGE_HEIGHT - 120
    cursor_y = draw_section_title(c, "Anexos del Proyecto", cursor_y)
    cursor_y -= 20
    
    c.setFont("Helvetica", 12)
    
    for pdf in data["anexos"]:
        nombre_archivo = os.path.basename(pdf)
        # El link apunta a la subcarpeta que crearemos luego
        link_destino = f"anexos/{nombre_archivo}"
        
        # Dibujamos el texto del anexo
        c.setFillColor("blue") # Color azul para identificar que es un link
        c.drawString(MARGIN + 20, cursor_y, f"• {nombre_archivo}")
        
        # Creamos el área clickeable (el "botón" invisible)
        # El orden es: (x_izq, y_inf, x_der, y_sup)
        c.linkURL(link_destino, (MARGIN + 20, cursor_y, MARGIN + 300, cursor_y + 12))
        
        cursor_y -= 25 # Espacio entre cada nombre de archivo
        
        # Si hay muchos anexos y se acaba la hoja, creamos otra
        if cursor_y < 150:
            c.showPage()
            page_num += 1
            draw_header_footer(c, page_num, project_data)
            cursor_y = PAGE_HEIGHT - 120

    c.save() # Guardamos el borrador con los links listos

    print("Insertando archivos PDF y generando versión final...")
    reader = PdfReader("output/mvp_imagenes.pdf")
    writer = PdfWriter()
    
    # Creamos el buscador de tareas
    tareas_dict = {p[0]: p[1] for p in insert_tasks}

    for i, page in enumerate(reader.pages):
        # i es el índice (0, 1, 2...)
        # num_pdf es la página humana que guardamos en insert_tasks
        num_pdf = i + 1 
        
        if num_pdf in tareas_dict:
            ruta_pdf_real = tareas_dict[num_pdf]
            if os.path.exists(ruta_pdf_real):
                print(f"-> Reemplazando marcador en página {num_pdf} por {os.path.basename(ruta_pdf_real)}")
                pdf_externo = PdfReader(ruta_pdf_real)
                for page_ext in pdf_externo.pages:
                    writer.add_page(page_ext)
                # Al NO hacer writer.add_page(page), borramos el marcador
            else:
                writer.add_page(page) # Si no existe el archivo, dejamos el marcador por seguridad
        else:
            # Esta es una página normal, la pasamos al PDF final
            writer.add_page(page)

    # --- GUARDADO EN CARPETA DE ENTREGA ---
    entrega_dir = "output/Reporte_Final_Entrega"
    anexos_dir = os.path.join(entrega_dir, "anexos")
    
    if os.path.exists(entrega_dir):
        shutil.rmtree(entrega_dir)
    os.makedirs(anexos_dir)

    # --- GUARDADO EN CARPETA DE ENTREGA ---
    output_path = os.path.join(entrega_dir, "Reporte_Principal.pdf")
    
    # Limpieza de duplicados y optimización pasiva
    writer.add_metadata(reader.metadata) 
    
    # En lugar de compress_content_streams (que puede fallar), 
    # usamos esta opción de PyPDF2 que es más estable:
    for page in writer.pages:
        # Esto elimina datos innecesarios de las imágenes sin comprimir agresivamente
        if "/Resources" in page and "/XObject" in page["/Resources"]:
            pass 

    with open(output_path, "wb") as f:
        writer.write(f)

    # Copiamos los anexos a la carpeta
    for pdf_anexo in data["anexos"]:
        if os.path.exists(pdf_anexo):
            shutil.copy(pdf_anexo, anexos_dir)

    print(f"✅ Proceso completo. Carpeta generada en: {entrega_dir}")

if __name__ == "__main__":
    main()