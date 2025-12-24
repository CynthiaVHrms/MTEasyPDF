import zipfile
import os
import shutil

from collections import defaultdict

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from pdf_utils import draw_images

from pdf_layout import (
    draw_cover,
    draw_header_footer,
    draw_section_title,
    draw_subsection_title,
    nueva_pagina_con_titulo,
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

def limpiar_temp():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)


def extraer_zip(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(TEMP_DIR)


def obtener_carpeta_raiz(base_path):
    carpetas = [
        os.path.join(base_path, c)
        for c in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, c))
    ]
    return carpetas[0] if len(carpetas) == 1 else base_path


# ============================================================
# DATA CLASIFICATION
# ============================================================

def clasificar_archivos(base_path):
    resultado = {
        "ubicacion": [],
        "inventario": [],
        "mantenimiento": {"imagenes": [], "pdfs": []},
        "anexos": [],
    }

    for carpeta in os.listdir(base_path):
        ruta_carpeta = os.path.join(base_path, carpeta)
        if not os.path.isdir(ruta_carpeta):
            continue

        nombre = carpeta.lower()

        if nombre.startswith("01"):
            continue

        if nombre.startswith("02"):
            for root, _, files in os.walk(ruta_carpeta):
                for f in sorted(files):
                    if f.lower().endswith((".jpg", ".jpeg", ".png")):
                        resultado["ubicacion"].append(os.path.join(root, f))

        elif nombre.startswith("03"):
            for root, _, files in os.walk(ruta_carpeta):
                for f in files:
                    if f.lower().endswith((".xls", ".xlsx", ".pdf")):
                        resultado["inventario"].append(os.path.join(root, f))

        elif "mantenimiento" in nombre or "implementacion" in nombre:
            for root, _, files in os.walk(ruta_carpeta):
                for f in sorted(files):
                    ruta = os.path.join(root, f)
                    if f.lower().endswith((".jpg", ".jpeg", ".png")):
                        resultado["mantenimiento"]["imagenes"].append(ruta)
                    elif f.lower().endswith(".pdf"):
                        resultado["mantenimiento"]["pdfs"].append(ruta)

        elif "anexos" in nombre:
            for root, _, files in os.walk(ruta_carpeta):
                for f in sorted(files):
                    if f.lower().endswith(".pdf"):
                        resultado["anexos"].append(os.path.join(root, f))

    return resultado


def imprimir_resumen(data):
    print("\n📍 Ubicación:", len(data["ubicacion"]), "imágenes")
    print("📊 Inventario:", len(data["inventario"]), "archivo(s)")
    print("🛠️ Mantenimiento:")
    print("   - imágenes:", len(data["mantenimiento"]["imagenes"]))
    print("   - pdfs:", len(data["mantenimiento"]["pdfs"]))
    print("📎 Anexos:", len(data["anexos"]), "pdf(s)")


# ============================================================
# PATH PARSING
# ============================================================

def limpiar_nombre(nombre):
    return (
        nombre.replace("_", " ")
        .replace("-", " ")
        .replace(".", "")
        .strip()
    )


def obtener_niveles(path, raiz):
    rel = os.path.relpath(path, raiz)
    partes = rel.split(os.sep)

    return {
        "seccion": limpiar_nombre(partes[0]) if len(partes) > 0 else None,
        "subseccion": limpiar_nombre(partes[1]) if len(partes) > 1 else None,
        "grupo": limpiar_nombre(partes[2]) if len(partes) > 2 else None,
        "categoria": limpiar_nombre(partes[-2]) if len(partes) >= 2 else None,
    }


# ============================================================
# MANTENIMIENTO TREE
# ============================================================

def build_mantenimiento_tree(imagenes, raiz):
    tree = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )

    for img in imagenes:
        niveles = obtener_niveles(img, raiz)
        tree[
            niveles["seccion"]
        ][
            niveles["subseccion"]
        ][
            niveles["grupo"]
        ][
            niveles["categoria"]
        ].append(img)

    return tree


def render_mantenimiento(canvas, page_num, cursor_y, tree, project_data):
    MIN_BOTTOM = 120  # margen seguro abajo (logos + número + aire)
    TITLE_GAP = 20    # espacio extra después de cada título/subtítulo

    for seccion, subsecciones in tree.items():

        page_num, cursor_y = nueva_pagina_con_titulo(
            canvas, page_num, project_data, seccion
        )
        cursor_y -= TITLE_GAP  # ✅ separación real tras título de sección

        for subseccion, grupos in subsecciones.items():
            if subseccion:
                # si no cabe el subtítulo, nueva página
                if cursor_y < (MIN_BOTTOM + 40):
                    canvas.showPage()
                    page_num += 1
                    draw_header_footer(canvas, page_num, project_data)
                    cursor_y = PAGE_HEIGHT - 100

                cursor_y = draw_subsection_title(canvas, subseccion, cursor_y)  # ✅ usa retorno
                cursor_y -= TITLE_GAP

            for grupo, categorias in grupos.items():
                if grupo:
                    if cursor_y < (MIN_BOTTOM + 40):
                        canvas.showPage()
                        page_num += 1
                        draw_header_footer(canvas, page_num, project_data)
                        cursor_y = PAGE_HEIGHT - 100

                    cursor_y = draw_subsection_title(canvas, grupo, cursor_y)  # ✅ usa retorno
                    cursor_y -= TITLE_GAP

                for categoria, imagenes in categorias.items():
                    # Si viene título de categoría, asegúrate que quepa antes de dibujarlo
                    if categoria:
                        if cursor_y < (MIN_BOTTOM + 40):
                            canvas.showPage()
                            page_num += 1
                            draw_header_footer(canvas, page_num, project_data)
                            cursor_y = PAGE_HEIGHT - 100

                        cursor_y = draw_subsection_title(canvas, categoria, cursor_y)  # ✅ usa retorno
                        cursor_y -= TITLE_GAP

                    nombre = (categoria or "").lower()
                    layout = 2 if ("pantalla" in nombre or "portada" in nombre) else 4

                    # Dibuja bloques de imágenes
                    while imagenes:
                        #  si no hay espacio suficiente, nueva página (antes de dibujar)
                        if cursor_y < (MIN_BOTTOM + 250):
                            canvas.showPage()
                            page_num += 1
                            draw_header_footer(canvas, page_num, project_data)
                            cursor_y = PAGE_HEIGHT - 100

                        imagenes, used_height = draw_images(
                            canvas,
                            imagenes,
                            per_page=layout,
                            start_y=cursor_y,
                        )

                        cursor_y -= used_height
                    canvas.showPage()
                    page_num += 1
                    draw_header_footer(canvas, page_num, project_data)
                    cursor_y = PAGE_HEIGHT - 100

    return page_num, cursor_y


# ============================================================
# MAIN
# ============================================================

def main():

    limpiar_temp()
    extraer_zip(ZIP_PATH)

    raiz = obtener_carpeta_raiz(TEMP_DIR)
    data = clasificar_archivos(raiz)

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

    draw_header_footer(c, page_num, project_data)

   # ---------------- UBICACIÓN ----------------
    page_num = 1
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

    # ---------------- MANTENIMIENTO ----------------
    mantenimiento_tree = build_mantenimiento_tree(
        data["mantenimiento"]["imagenes"], raiz
    )

    page_num, cursor_y = render_mantenimiento(
        c, page_num, cursor_y, mantenimiento_tree, project_data
    )

    c.save()
    imprimir_resumen(data)


if __name__ == "__main__":
    main()
