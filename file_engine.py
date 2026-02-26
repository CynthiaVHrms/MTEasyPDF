import os 
import re
import zipfile
import shutil
from collections import defaultdict

NO_SUBSECCION = "__SIN_UBICACION__"


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

def limpiar_nombre_completo(nombre):
    # Primero quitamos numeración inicial tipo "01 ", "01. ", "01-" 
    nombre_limpio = re.sub(r'^\d+[\s.\-_]*', '', nombre)
    # Luego aplicamos tu limpieza de caracteres
    return nombre_limpio.replace("_", " ").replace("-", " ").replace(".", "").strip()


def obtener_niveles(path, raiz):
    rel = os.path.relpath(path, raiz)
    partes = rel.split(os.sep)
    
    # Estructura base
    res = {
        "seccion": partes[0] if len(partes) > 0 else "Mantenimiento",
        "subseccion": partes[1] if len(partes) > 1 else "General",
        "grupo": partes[2] if len(partes) > 2 else "General",
        "categoria": "" # Por defecto vacío para que no diga "Fotos"
    }

    # Si hay nivel 4 o más
    if len(partes) >= 4:
        # Extraemos todas las carpetas desde la 4ta (partes[3]) hasta la última carpeta (partes[-2])
        # Limpiamos cada una individualmente para quitar números
        extras = [limpiar_nombre_completo(p) for p in partes[3:-1]]
        # Las unimos con un separador limpio
        res["categoria"] = " - ".join(extras)
        
    return res


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


def build_mantenimiento_tree(imagenes, raiz, usa_ubicacion=True):
    tree = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    for img in imagenes:
        if not img.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        niveles = obtener_niveles(img, raiz)

        # Extraemos los niveles ya procesados
        seccion = limpiar_nombre(niveles.get("seccion"))
        
        if usa_ubicacion:
            subseccion = limpiar_nombre(niveles.get("subseccion", "Ubicación"))
            grupo = limpiar_nombre(niveles.get("grupo", "General"))
        else:
            # Si no hay ubicación, mantenemos la jerarquía pero bajo nombres genéricos
            subseccion = limpiar_nombre(niveles.get("subseccion", "General"))
            grupo = limpiar_nombre(niveles.get("grupo", "General"))

        # La categoría ya viene con el 5to nivel unido si existía
        categoria = limpiar_nombre(niveles.get("categoria", "Fotos"))

        tree[seccion][subseccion][grupo][categoria].append(img)

    return tree


def agrupar_pdfs_por_categoria(pdfs, raiz, usa_ubicacion=True):
    pdf_tree = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )

    for pdf in pdfs:
        niveles = obtener_niveles(pdf, raiz)
        seccion = niveles.get("seccion", "General")

        if not usa_ubicacion:
            # MODO SIN UBICACIÓN:
            # Saltamos el nivel de subsección para que no haya títulos vacíos
            subseccion = ""
            # Subimos el grupo y la categoría un nivel
            grupo = niveles.get("subseccion", "Documentación Técnica")
            categoria = niveles.get("grupo", "Anexos")
        else:
            # MODO CON UBICACIÓN:
            # Mantenemos la estructura de 4 niveles
            subseccion = niveles.get("subseccion", "Ubicación General")
            grupo = niveles.get("grupo", "Documentación Técnica")
            categoria = niveles.get("categoria", "Anexos")

        # Guardamos en el árbol con la jerarquía corregida
        pdf_tree[seccion][subseccion][grupo][categoria].append(pdf)

    return pdf_tree


def calcular_paginas_indice(mantenimiento_tree, data, usa_ubicacion=True):
    # Estimamos 35 líneas por página
    lineas_por_pagina = 35

    # Iniciamos conteo con Ubicación, Inventario y Anexos
    conteo_ubicacion = 1 if (usa_ubicacion and data.get("ubicacion")) else 0
    total_items = conteo_ubicacion + len(data["inventario"]) + 1

    # Sumamos los niveles del árbol de mantenimiento
    for seccion, sub in mantenimiento_tree.items():
        total_items += 1  # Nivel 1
        for sub_sec, grupos in sub.items():
            if sub_sec:
                total_items += 1  # Nivel 2
            for grupo, categorias in grupos.items():
                if grupo:
                    total_items += 1  # Nivel 3
                # Si las categorías también van al índice, sumarlas aquí
                # total_items += len(categorias)

    # Cálculo de páginas (redondeo hacia arriba)
    return (total_items + lineas_por_pagina - 1) // lineas_por_pagina
