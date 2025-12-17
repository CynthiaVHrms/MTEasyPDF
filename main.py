import zipfile
import os
import shutil
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pdf_utils import draw_images
from pdf_layout import (
    draw_cover,
    draw_header_footer,
    draw_section_title
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_PATH = "ejemplo.zip"  # cambia el nombre luego
TEMP_DIR = "temp"


project_data = {
    "titulo": "Reporte de Evidencias",
    "info_extra": "Proyecto MT - Marzo 2025",
    "introduccion": "Este documento contiene las evidencias recopiladas durante el proyecto MT.",
    "imagen_portada": os.path.join(BASE_DIR, "input", "portada.jpg"),
    "logo_sup_izq": os.path.join(BASE_DIR, "input", "logo_izq.png"),
    "logo_sup_der": os.path.join(BASE_DIR, "input", "logo_der.png"),
    "logo_inf_izq": os.path.join(BASE_DIR, "input", "logo_izq.png"),
    "logo_inf_der": os.path.join(BASE_DIR, "input", "logo_der.png"),
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
    draw_header_footer(canvas, page_num, {
        "logo_izq": project_data["logo_sup_izq"],
        "logo_der": project_data["logo_sup_der"],
    })
    return page_num


def main():
    limpiar_temp()
    extraer_zip(ZIP_PATH)

    raiz = obtener_carpeta_raiz(TEMP_DIR)
    data = clasificar_archivos(raiz)

    c = canvas.Canvas(
    "output/mvp_imagenes.pdf",
    pagesize=A4,
    pageCompression=1
)
    page_num = 0
    
    draw_cover(c, {
        "titulo": project_data["titulo"],
        "info_extra": project_data["info_extra"],
        "imagen_portada": project_data["imagen_portada"],
    })

    # PRUEBA: ubicación
    if data["ubicacion"]:
        page_num = nueva_pagina(c, page_num, project_data)
        draw_section_title(c, "Ubicación")

        if len(data["ubicacion"]) == 1:
            draw_images(c, data["ubicacion"], per_page=1)
        else:
            draw_images(c, data["ubicacion"], per_page=2)

    # PRUEBA: mantenimiento (todas como 4 por hoja por ahora)
    imagenes_4 = []
    imagenes_2 = []
    
    if data["mantenimiento"]["imagenes"]:
        page_num = nueva_pagina(c, page_num, project_data)
        draw_section_title(c, "Mantenimiento")


    for img in data["mantenimiento"]["imagenes"]:
        ruta = img.lower()
        if "pruebas" in ruta or "pantallas" in ruta:
            imagenes_2.append(img)
        else:
            imagenes_4.append(img)

    if imagenes_4:
        draw_images(c, imagenes_4, per_page=4)

    if imagenes_2:
        draw_images(c, imagenes_2, per_page=2)


    c.save()


    imprimir_resumen(data)

if __name__ == "__main__":
    main()