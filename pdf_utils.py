import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PIL import Image

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40
TEXT_HEIGHT = 14
TOP_SAFE_MARGIN = PAGE_HEIGHT - 200


def prepare_image_for_pdf(path, max_width=1400, quality=65):
    img = Image.open(path).convert("RGB")

    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize(
            (int(img.width * ratio), int(img.height * ratio)),
            Image.LANCZOS
        )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    img.close()
    return buf


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

        canvas.setFillColorRGB(0, 0, 0)
        canvas.setFont("Helvetica", 7)
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
