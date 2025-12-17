import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40


def draw_cover(canvas, data):
    """
    Dibuja la portada del documento
    """
    def draw_cover(canvas, data):
        if not os.path.exists(data["imagen_portada"]):
            raise FileNotFoundError(
                f"No se encontró la imagen de portada: {data['imagen_portada']}"
            )
    canvas.setFont("Helvetica-Bold", 24)
    canvas.drawCentredString(
        PAGE_WIDTH / 2,
        PAGE_HEIGHT - 120,
        data["titulo"]
    )

    canvas.setFont("Helvetica", 12)
    canvas.drawCentredString(
        PAGE_WIDTH / 2,
        PAGE_HEIGHT - 160,
        data.get("info_extra", "")
    )

    if data.get("imagen_portada"):
        canvas.drawImage(
            data["imagen_portada"],
            MARGIN,
            PAGE_HEIGHT / 2 - 150,
            width=PAGE_WIDTH - 2 * MARGIN,
            height=300,
            preserveAspectRatio=True
        )

    canvas.showPage()


def draw_header_footer(canvas, page_num, data):
    """
    Header y pie de página
    """
    # Header
    if data.get("logo_izq"):
        canvas.drawImage(
            data["logo_izq"],
            MARGIN,
            PAGE_HEIGHT - 50,
            width=60,
            height=30,
            preserveAspectRatio=True
        )

    if data.get("logo_der"):
        canvas.drawImage(
            data["logo_der"],
            PAGE_WIDTH - MARGIN - 60,
            PAGE_HEIGHT - 50,
            width=60,
            height=30,
            preserveAspectRatio=True
        )

    # Footer
    canvas.setFont("Helvetica", 9)
    canvas.setFillColor(black)
    canvas.drawCentredString(
        PAGE_WIDTH / 2,
        25,
        f"Página {page_num}"
    )


def draw_section_title(canvas, title):
    """
    Título de cada sección
    """
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(
        MARGIN,
        PAGE_HEIGHT - 100,
        title
    )

    canvas.line(
        MARGIN,
        PAGE_HEIGHT - 110,
        PAGE_WIDTH - MARGIN,
        PAGE_HEIGHT - 110
    )
