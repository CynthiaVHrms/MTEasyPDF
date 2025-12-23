import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageOps


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40
TEXT_HEIGHT = 14
MAX_PIXELS = 1200
TOP_SAFE_MARGIN = PAGE_HEIGHT - 200


def load_normalized_image(path):
    img = Image.open(path)
    return img


def draw_images(canvas, images, per_page=4, start_y=None, y_offset=0):
    """
    Dibuja imágenes sin solaparse.
    start_y = punto desde donde empiezan las imágenes (debajo del título)
    """

    # =========================
    # 🔹 POSICIONES HORIZONTALES (NO CAMBIAN)
    # =========================
    if per_page == 1:
        x_positions = [PAGE_WIDTH / 2]

    elif per_page == 2:
        x_positions = [PAGE_WIDTH / 2]

    elif per_page == 4:
        x_positions = [PAGE_WIDTH * 0.27, PAGE_WIDTH * 0.73]


    # =========================
    # 🔹 POSICIONES VERTICALES (NUEVO CONTROL)
    # =========================
    if start_y is None:
        start_y = TOP_SAFE_MARGIN  # fallback seguro
        
    start_y -= 120 # espacio para título sección

    if per_page == 1:
        row_offsets = [0]

    elif per_page == 2:
        row_offsets = [0, 360]  # misma separación visual que tenías

    elif per_page == 4:
        row_offsets = [0, 300]  # 🔥 AQUÍ controlas separación vertical


    # =========================
    # 🔹 TAMAÑO DE CAJA (NO CAMBIA)
    # =========================
    if per_page == 4:
        max_w, max_h = 240, 190
    elif per_page == 2:
        max_w, max_h = 360, 290
    else:
        max_w, max_h = 420, 380


    idx = 0

    images_to_draw = images[:per_page]
    remaining_images = images[per_page:]

    for img_path in images_to_draw:

        buffer = None
        try:
            img = load_normalized_image(img_path)
        except Exception:
            print(f"⚠️ No se pudo cargar imagen: {img_path}")
            idx += 1
            continue

        pos = idx % per_page
        col = pos % len(x_positions)
        row = pos // len(x_positions)

        x = x_positions[col]
        y = start_y - row_offsets[row]


        # =========================
        # 🔹 ESCALADO (NO CAMBIA)
        # =========================
        iw, ih = img.size

        if max(iw, ih) > MAX_PIXELS:
            img.thumbnail((MAX_PIXELS, MAX_PIXELS), Image.LANCZOS)
            iw, ih = img.size

        img = img.convert("RGB")

        scale = min(max_w / iw, max_h / ih)
        draw_w = iw * scale
        draw_h = ih * scale


        # =========================
        # 🔹 CAJA DE FONDO (NO CAMBIA)
        # =========================
        canvas.setFillColorRGB(0.97, 0.97, 0.97)
        canvas.rect(
            x - max_w / 2,
            y - max_h / 2,
            max_w,
            max_h,
            fill=1,
            stroke=0
        )


        # =========================
        # 🔹 DIBUJO DE IMAGEN (NO CAMBIA)
        # =========================
        img_reader = ImageReader(img)

        canvas.drawImage(
            img_reader,
            x - draw_w / 2,
            y - draw_h / 2,
            width=draw_w,
            height=draw_h,
            preserveAspectRatio=True
        )


        # =========================
        # 🔹 NOMBRE DE ARCHIVO
        # =========================
        filename = img_path.split("\\")[-1].rsplit(".", 1)[0]
        canvas.setFillColorRGB(0, 0, 0)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(
            x,
            y - max_h / 2 - TEXT_HEIGHT,
            filename
        )


        idx += 1
        img.close()

        if buffer:
            buffer.close()
            
    return remaining_images