import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PIL import Image, ImageOps


PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40
TEXT_HEIGHT = 14
MAX_PIXELS = 1200

def load_normalized_image(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)  # corrige rotación
    return img

def draw_images(canvas, images, per_page):
    x_positions = []
    y_positions = []

    if per_page == 1:
        x_positions = [PAGE_WIDTH / 2]
        y_positions = [PAGE_HEIGHT / 2]
    elif per_page == 2:
        x_positions = [PAGE_WIDTH / 2]
        y_positions = [
            PAGE_HEIGHT * 0.70,
            PAGE_HEIGHT * 0.30
        ]
    elif per_page == 4:
        x_positions = [PAGE_WIDTH / 4, 3 * PAGE_WIDTH / 4]
        y_positions = [
            PAGE_HEIGHT * 0.62,
            PAGE_HEIGHT * 0.32
        ]

    idx = 0

    for img_path in images:
        try:
            img = load_normalized_image(img_path)
        except Exception as e:
            print(f"⚠️ No se pudo cargar imagen: {img_path}")
            idx += 1
            continue

        if idx > 0 and idx % per_page == 0:
            canvas.showPage()

        pos = idx % per_page
        x = x_positions[pos % len(x_positions)]
        y = y_positions[pos // len(x_positions)]

        # Definir caja máxima según layout
        if per_page == 4:
            max_w, max_h = 260, 180
        elif per_page == 2:
            max_w, max_h = 400, 300
        else:  # per_page == 1
            max_w, max_h = 400, 300
            
        iw, ih = img.size

        if max(iw, ih) > MAX_PIXELS:
            img.thumbnail((MAX_PIXELS, MAX_PIXELS), Image.LANCZOS)
            iw, ih = img.size

        img = img.convert("RGB")

        # Escala respetando proporción
        scale = min(max_w / iw, max_h / ih)

        draw_w = iw * scale
        draw_h = ih * scale
        
        canvas.setFillColorRGB(0.95, 0.95, 0.95)
        canvas.rect(
            x - max_w / 2,
            y - max_h / 2,
            max_w,
            max_h,
            fill=1,
            stroke=1
        )
        
        buffer = None

        if max(iw, ih) > 800:
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=80, optimize=True)
            buffer.seek(0)
            img_reader = ImageReader(buffer)
        else:
            img_reader = ImageReader(img)


        canvas.drawImage(
        img_reader,
        x - draw_w / 2,
        y - draw_h / 2,
        width=draw_w,
        height=draw_h,
        preserveAspectRatio=True
        )

        filename = img_path.split("\\")[-1].rsplit(".", 1)[0]
        canvas.setFillColorRGB(0, 0, 0)
        canvas.setFont("Helvetica", 8)
        canvas.drawCentredString(
            x,
            y - draw_h / 2 - TEXT_HEIGHT,
            filename
        )

        idx += 1
        img.close()
        if buffer:
            buffer.close()


    if idx % per_page != 0:
        canvas.showPage()