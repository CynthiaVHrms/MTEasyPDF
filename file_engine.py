import os
import zipfile
import shutil
from collections import defaultdict

def limpiar_temp(temp_dir):
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)

def extraer_zip(zip_path, temp_dir):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

def obtener_carpeta_raiz(base_path):
    carpetas = [
        os.path.join(base_path, c)
        for c in os.listdir(base_path)
        if os.path.isdir(os.path.join(base_path, c))
    ]
    return carpetas[0] if len(carpetas) == 1 else base_path

def limpiar_nombre(nombre):
    return nombre.replace("_", " ").replace("-", " ").replace(".", "").strip()

def obtener_niveles(path, raiz):
    rel = os.path.relpath(path, raiz)
    partes = rel.split(os.sep)
    return {
        "seccion": limpiar_nombre(partes[0]) if len(partes) > 0 else None,
        "subseccion": limpiar_nombre(partes[1]) if len(partes) > 1 else None,
        "grupo": limpiar_nombre(partes[2]) if len(partes) > 2 else None,
        "categoria": limpiar_nombre(partes[-2]) if len(partes) >= 2 else None,
    }

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


def build_mantenimiento_tree(imagenes, raiz):
    tree = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )

    for img in imagenes:
        niveles = obtener_niveles(img, raiz)
        tree[niveles["seccion"]][niveles["subseccion"]][niveles["grupo"]][
            niveles["categoria"]
        ].append(img)

    return tree


def agrupar_pdfs_por_categoria(pdfs, raiz):
    pdf_tree = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )

    for pdf in pdfs:
        niveles = obtener_niveles(pdf, raiz)
        pdf_tree[niveles["seccion"]][niveles["subseccion"]][niveles["grupo"]][
            niveles["categoria"]
        ].append(pdf)

    return pdf_tree