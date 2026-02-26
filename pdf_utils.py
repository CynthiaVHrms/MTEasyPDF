import io
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PIL import Image
from collections import defaultdict

from file_engine import (
    obtener_niveles,
)

from pdf_layout import (
    draw_header_footer,
    draw_section_title,
)

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40
TEXT_HEIGHT = 14
TOP_SAFE_MARGIN = PAGE_HEIGHT - 100


def prepare_image_for_pdf(path, max_width=1000, quality=50):
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            if img.width > max_width:
                ratio = max_width / img.width
                # Usar Resampling.LANCZOS para Pillow actualizado
                img = img.resize(
                    (int(img.width * ratio), int(img.height * ratio)),
                    Image.Resampling.LANCZOS,
                )

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            buf.seek(0)
            return buf
    except Exception as e:
        print(f"Error procesando imagen {path}: {e}")
        return None


def draw_images(canvas, images, per_page=4, start_y=None):

    def clean_filename(name):
        return name.lstrip("0123456789.- _").strip()

    """
    Dibuja un bloque (hasta per_page imágenes) y regresa:
      (remaining_images, used_height)

    used_height = altura REAL consumida para que el main pueda mover cursor_y correctamente.
    """

    if start_y is None:
        start_y = TOP_SAFE_MARGIN

    # ------------------------------------------------------------
    # Layout: columnas/filas
    # ------------------------------------------------------------
    if per_page in (1, 2):
        # 1 columna centrada (2 filas si per_page==2 y hay 2 imgs)
        x_positions = [PAGE_WIDTH / 2]
    else:
        # 2 columnas
        x_positions = [PAGE_WIDTH * 0.27, PAGE_WIDTH * 0.73]

    # Tamaños máximos por celda
    if per_page == 4:
        max_w, max_h = 235, 220
    elif per_page == 2:
        max_w, max_h = 400, 250
    else:  # per_page == 1
        max_w, max_h = 400, 250

    images_to_draw = images[:per_page]
    remaining_images = images[per_page:]

    # filas reales que se van a usar
    cols = len(x_positions)
    rows = (len(images_to_draw) + cols - 1) // cols

    # espaciado vertical real por fila (incluye texto)
    row_gap = max_h + TEXT_HEIGHT + 48  # 28 = padding visual (se ve bien)
    top_padding = 10
    bottom_padding = 20

    # altura real consumida por este bloque
    used_height = top_padding + (rows * row_gap) + bottom_padding

    # ------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------
    idx = 0
    for img_path in images_to_draw:
        try:
            buf = prepare_image_for_pdf(img_path)
            img_reader = ImageReader(buf)
            iw, ih = img_reader.getSize()
        except Exception:
            print(f"⚠️ No se pudo cargar imagen: {img_path}")
            idx += 1
            continue

        col = idx % cols
        row = idx // cols

        x = x_positions[col]

        # Centro vertical de la celda de esa fila
        # Primera fila se coloca debajo de start_y respetando top_padding
        cell_center_y = start_y - top_padding - (row * row_gap) - (max_h / 2)

        # Escalado
        scale = min(max_w / iw, max_h / ih)
        draw_w = iw * scale
        draw_h = ih * scale

        # Fondo de la celda
        canvas.setFillColorRGB(0.97, 0.97, 0.97)
        canvas.rect(
            x - max_w / 2,
            cell_center_y - max_h / 2,
            max_w,
            max_h,
            fill=1,
            stroke=0,
        )

        # Imagen
        canvas.drawImage(
            img_reader,
            x - draw_w / 2,
            cell_center_y - draw_h / 2,
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True,
            mask="auto",
        )

        # Texto (nombre archivo)
        raw_name = img_path.split("\\")[-1].rsplit(".", 1)[0]
        filename = clean_filename(raw_name)
        tiene_letras = bool(re.search("[a-zA-Z]", filename))

        if tiene_letras:
            canvas.setFillColorRGB(0, 0, 0)
            canvas.setFont("Arial", 12)
            canvas.drawCentredString(
                x,
                (cell_center_y - max_h / 2) - TEXT_HEIGHT,
                filename,
            )

        try:
            buf.close()
        except Exception:
            pass

        idx += 1

    return remaining_images, used_height


def draw_images_by_rows(
    canvas,
    images,
    images_per_row=2,
    start_y=None,
    project_data=None,
    seccion="",
    callback_progreso=None,
    total_imagenes=None,
    imagenes_procesadas_ref=None,
):
    import re

    if start_y is None:
        start_y = TOP_SAFE_MARGIN

    def clean_filename(name):
        return name.lstrip("0123456789.- _").strip()

    cursor_y = start_y

    # Configuración de tamaños
    if images_per_row == 1:
        max_w, max_h = 400, 240  # Bajamos 10px el alto para asegurar que quepan 2 filas
        x_positions = [PAGE_WIDTH / 2]
    else:
        max_w, max_h = 235, 220
        x_positions = [PAGE_WIDTH * 0.27, PAGE_WIDTH * 0.73]

    # Reducimos el gap de 40 a 30 para ganar espacio
    row_gap = max_h + TEXT_HEIGHT + 30
    bottom_limit = 80  # Bajamos el límite para permitir exprimir más la hoja

    idx = 0
    while idx < len(images):
        row_images = images[idx : idx + images_per_row]

        # Si es la PRIMERA fila y el cursor ya viene muy abajo, saltamos
        # Si no es la primera, evaluamos si cabe la siguiente
        if cursor_y - row_gap < bottom_limit:
            canvas.showPage()
            draw_header_footer(canvas, canvas.getPageNumber(), project_data)
            cursor_y = draw_section_title(canvas, seccion, TOP_SAFE_MARGIN)
            cursor_y -= 10

        for col, img_path in enumerate(row_images):
            try:
                buf = prepare_image_for_pdf(img_path)
                img_reader = ImageReader(buf)
                iw, ih = img_reader.getSize()

                x = x_positions[col]
                center_y = cursor_y - (max_h / 2)
                scale = min(max_w / iw, max_h / ih)

                canvas.setFillColorRGB(0.97, 0.97, 0.97)
                canvas.rect(
                    x - max_w / 2, center_y - max_h / 2, max_w, max_h, fill=1, stroke=0
                )

                canvas.drawImage(
                    img_reader,
                    x - (iw * scale) / 2,
                    center_y - (ih * scale) / 2,
                    width=iw * scale,
                    height=ih * scale,
                    preserveAspectRatio=True,
                    mask="auto",
                )

                filename = clean_filename(img_path.split("\\")[-1].rsplit(".", 1)[0])
                if bool(re.search("[a-zA-Z]", filename)):
                    canvas.setFillColorRGB(0, 0, 0)
                    canvas.setFont("Arial", 11)
                    canvas.drawCentredString(x, center_y - max_h / 2 - 12, filename)
                buf.close()
                del img_reader
                
            # ---- ACTUALIZAR PROGRESO ----
                if callback_progreso and total_imagenes and imagenes_procesadas_ref is not None:
                    imagenes_procesadas_ref[0] += 1
                    progreso_local = imagenes_procesadas_ref[0] / total_imagenes
                    callback_progreso(30 + int(40 * progreso_local))    
            except:
                continue

        canvas.setFillColorRGB(0, 0, 0)
        cursor_y -= row_gap
        idx += images_per_row

    return cursor_y


def build_pdf_tree(archivos, raiz, usa_ubicacion=True):
    tree = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )

    for archivo in archivos:
        if not archivo.lower().endswith(".pdf"):
            continue

        niveles = obtener_niveles(archivo, raiz)
        tree[niveles["seccion"]][niveles["subseccion"]][niveles["grupo"]][
            niveles["categoria"]
        ].append(archivo)

    return tree
