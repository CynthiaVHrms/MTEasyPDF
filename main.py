import zipfile
import os
import shutil
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pdf_utils import draw_images
from collections import defaultdict
from pdf_layout import (
    draw_cover,
    draw_header_footer,
    draw_section_title,
    draw_subsection_title,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_PATH = "ejemplo.zip"  # cambia el nombre luego
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


def limpiar_temp():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)


def extraer_zip(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(TEMP_DIR)


def obtener_carpeta_raiz(base_path):
    contenidos = os.listdir(base_path)
    carpetas = [
        os.path.join(base_path, c)
        for c in contenidos
        if os.path.isdir(os.path.join(base_path, c))
    ]

    # Si hay una sola carpeta, esa es la raíz real
    if len(carpetas) == 1:
        return carpetas[0]

    # Si hay varias, usamos base_path
    return base_path


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

        # Ignorar introducción
        if nombre.startswith("01"):
            continue

        # Ubicación
        if nombre.startswith("02"):
            for root, _, files in os.walk(ruta_carpeta):
                for f in sorted(files):
                    if f.lower().endswith((".jpg", ".jpeg", ".png")):
                        resultado["ubicacion"].append(os.path.join(root, f))

        # Inventario
        elif nombre.startswith("03"):
            for root, _, files in os.walk(ruta_carpeta):
                for f in files:
                    if f.lower().endswith((".xls", ".xlsx", ".pdf")):
                        resultado["inventario"].append(os.path.join(root, f))

        # Mantenimiento o Implementación
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


from reportlab.pdfgen import canvas


def nueva_pagina(canvas, page_num, project_data):
    canvas.showPage()
    page_num += 1
    draw_header_footer(
        canvas,
        page_num,
        {
            "logo_izq": project_data["logo_sup_izq"],
            "logo_der": project_data["logo_sup_der"],
        },
    )
    return page_num


def limpiar_nombre(nombre):
    nombre = nombre.replace("_", " ")
    nombre = nombre.replace("-", " ")
    nombre = nombre.replace(".", "")
    nombre = nombre.strip()
    return nombre


def obtener_niveles(path, raiz):
    rel = os.path.relpath(path, raiz)
    partes = rel.split(os.sep)

    niveles = {
        "seccion": limpiar_nombre(partes[0]) if len(partes) > 0 else None,
        "subseccion": limpiar_nombre(partes[1]) if len(partes) > 1 else None,
        "grupo": limpiar_nombre(partes[2]) if len(partes) > 2 else None,
        "categoria": limpiar_nombre(partes[-2]) if len(partes) >= 2 else None,
    }

    return niveles


def asegurar_espacio_para_imagenes(
    canvas, page_num, project_data, cursor_y, layout_actual
):
    alto_bloque = 620 if layout_actual == 4 else 520

    if cursor_y - alto_bloque < 150:
        page_num = nueva_pagina(canvas, page_num, project_data)
        cursor_y = PAGE_HEIGHT - 100

    return page_num, cursor_y


def main():
    limpiar_temp()
    extraer_zip(ZIP_PATH)

    raiz = obtener_carpeta_raiz(TEMP_DIR)
    data = clasificar_archivos(raiz)

    c = canvas.Canvas("output/mvp_imagenes.pdf", pagesize=A4, pageCompression=1)
    page_num = 0
    cursor_y = PAGE_HEIGHT - 100

    draw_cover(
        c,
        {
            "titulo": project_data["titulo"],
            "info_extra": project_data["info_extra"],
            "imagen_portada": project_data["imagen_portada"],
        },
    )

    # PRUEBA: ubicación
    if data["ubicacion"]:
        page_num = nueva_pagina(c, page_num, project_data)

    cursor_y = draw_section_title(c, "Ubicación")

    if len(data["ubicacion"]) == 1:
        draw_images(
            c,
            data["ubicacion"],
            per_page=1,
            start_y=cursor_y,
        )
    else:
        draw_images(
            c,
            data["ubicacion"],
            per_page=2,
            start_y=cursor_y,
        )

    # reservar espacio por las imágenes de ubicación
    if len(data["ubicacion"]) == 1:
        cursor_y -= 480
    else:
        cursor_y -= 520

    # PRUEBA: mantenimiento (todas como 4 por hoja por ahora)
    current_folder = None

    # =========================
    # MANTENIMIENTO
    # =========================

    ultimo = {
        "seccion": None,
        "subseccion": None,
        "grupo": None,
        "categoria": None,
    }

    buffer_imagenes = []
    layout_actual = 4  # por defecto

    for img in data["mantenimiento"]["imagenes"]:
        niveles = obtener_niveles(img, raiz)

        # 🔸 Si cambia la SECCIÓN
        if niveles["seccion"] != ultimo["seccion"]:
            if buffer_imagenes:
                page_num, cursor_y = asegurar_espacio_para_imagenes(
                    c, page_num, project_data, cursor_y, layout_actual
                )

                draw_images(
                    c,
                    buffer_imagenes,
                    per_page=layout_actual,
                    start_y=cursor_y,
                )

                # reservar espacio después de dibujar
                if layout_actual == 4:
                    cursor_y -= 620
                else:
                    cursor_y -= 520

            buffer_imagenes = []

            page_num = nueva_pagina(c, page_num, project_data)
            cursor_y = draw_section_title(c, niveles["seccion"])

            ultimo["seccion"] = niveles["seccion"]
            ultimo["subseccion"] = None
            ultimo["grupo"] = None
            ultimo["categoria"] = None

        # 🔸 Si cambia la SUBSECCIÓN
        if niveles["subseccion"] != ultimo["subseccion"]:
            if buffer_imagenes:
                page_num, cursor_y = asegurar_espacio_para_imagenes(
                    c, page_num, project_data, cursor_y, layout_actual
                )

                draw_images(
                    c,
                    buffer_imagenes,
                    per_page=layout_actual,
                    start_y=cursor_y,
                )

                # reservar espacio después de dibujar
                if layout_actual == 4:
                    cursor_y -= 620
                else:
                    cursor_y -= 520

            buffer_imagenes = []

            if cursor_y < 200:
                page_num = nueva_pagina(c, page_num, project_data)
                cursor_y = PAGE_HEIGHT - 100

            cursor_y -= 20
            draw_subsection_title(c, niveles["subseccion"], cursor_y)
            cursor_y -= 30

            ultimo["subseccion"] = niveles["subseccion"]
            ultimo["grupo"] = None
            ultimo["categoria"] = None

        # 🔸 Si cambia el GRUPO
        if niveles["grupo"] != ultimo["grupo"]:
            if buffer_imagenes:
                page_num, cursor_y = asegurar_espacio_para_imagenes(
                    c, page_num, project_data, cursor_y, layout_actual
                )

                draw_images(
                    c,
                    buffer_imagenes,
                    per_page=layout_actual,
                    start_y=cursor_y,
                )

                # reservar espacio después de dibujar
                if layout_actual == 4:
                    cursor_y -= 620
                else:
                    cursor_y -= 520

            buffer_imagenes = []

            cursor_y -= 20
            draw_subsection_title(c, niveles["grupo"], cursor_y)
            cursor_y -= 30

            ultimo["grupo"] = niveles["grupo"]
            ultimo["categoria"] = None

        # 🔸 Si cambia la CATEGORÍA (Antes / Después / Documentación)
        if niveles["categoria"] != ultimo["categoria"]:
            if buffer_imagenes:
                page_num, cursor_y = asegurar_espacio_para_imagenes(
                    c, page_num, project_data, cursor_y, layout_actual
                )

                draw_images(
                    c,
                    buffer_imagenes,
                    per_page=layout_actual,
                    start_y=cursor_y,
                )

                # reservar espacio después de dibujar
                if layout_actual == 4:
                    cursor_y -= 620
                else:
                    cursor_y -= 520

            buffer_imagenes = []

            cursor_y -= 20
            draw_subsection_title(c, niveles["categoria"], cursor_y)
            cursor_y -= 30

            nombre_cat = (niveles["categoria"] or "").lower()

            # 📐 decidir layout
            if "pantalla" in nombre_cat or "portada" in nombre_cat:
                layout_actual = 2
            else:
                layout_actual = 4

            ultimo["categoria"] = niveles["categoria"]

        # ➕ acumular imagen
        buffer_imagenes.append(img)

    # 🔚 Dibujar lo que quedó pendiente
    if buffer_imagenes:
        page_num, cursor_y = asegurar_espacio_para_imagenes(
            c, page_num, project_data, cursor_y, layout_actual
        )
        draw_images(
            c,
            buffer_imagenes,
            per_page=layout_actual,
            start_y=cursor_y,
        )
        # reservar espacio después de dibujar
        if layout_actual == 4:
            cursor_y -= 620
        else:
            cursor_y -= 520
    buffer_imagenes = []

    c.save()

    imprimir_resumen(data)


if __name__ == "__main__":
    main()
