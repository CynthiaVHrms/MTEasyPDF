import os

from reportlab.lib.pagesizes import A4

from reportlab.lib.colors import black


PAGE_WIDTH, PAGE_HEIGHT = A4

MARGIN = 40


def draw_cover(canvas, data, project_data):
    """

    Dibuja la portada del documento

    """

    # Fondo claro opcional

    canvas.setFillColorRGB(0.95, 0.95, 0.95)

    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

    # Imagen de portada (opcional)

    imagen = data.get("imagen_portada")

    if imagen and os.path.exists(imagen):

        canvas.drawImage(
            imagen,
            MARGIN,
            PAGE_HEIGHT / 2 - 160,
            width=PAGE_WIDTH - 2 * MARGIN,
            height=320,
            preserveAspectRatio=True,
            mask="auto",
        )

    # Título

    canvas.setFillColorRGB(0, 0, 0)

    canvas.setFont("Helvetica-Bold", 26)

    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 140, data.get("titulo", ""))

    # Subtítulo / info extra

    canvas.setFont("Helvetica", 14)

    canvas.drawCentredString(
        PAGE_WIDTH / 2, PAGE_HEIGHT - 180, data.get("info_extra", "")
    )

    draw_header_footer(
        canvas,
        page_num=None,
        data={
            "logo_sup_izq": project_data["logo_sup_izq"],
            "logo_sup_der": project_data["logo_sup_der"],
            "logo_inf_izq": project_data["logo_inf_izq"],
            "logo_inf_der": project_data["logo_inf_der"],
        },
    )

    canvas.showPage()


def draw_header_footer(canvas, page_num, data):

    logo_size = 40

    padding = 20

    # 4 logos (todas las páginas)

    canvas.drawImage(
        data["logo_sup_izq"],
        padding,
        PAGE_HEIGHT - logo_size - padding,
        width=logo_size,
        height=logo_size,
        mask="auto",
    )

    canvas.drawImage(
        data["logo_sup_der"],
        PAGE_WIDTH - logo_size - padding,
        PAGE_HEIGHT - logo_size - padding,
        width=logo_size,
        height=logo_size,
        mask="auto",
    )

    canvas.drawImage(
        data["logo_inf_izq"],
        padding,
        padding,
        width=logo_size,
        height=logo_size,
        mask="auto",
    )

    canvas.drawImage(
        data["logo_inf_der"],
        PAGE_WIDTH - logo_size - padding,
        padding,
        width=logo_size,
        height=logo_size,
        mask="auto",
    )

    # SOLO número si NO es portada

    if page_num is not None:

        canvas.setFont("Helvetica", 8)

        canvas.drawCentredString(PAGE_WIDTH / 2, 15, str(page_num))


def draw_section_title(canvas, title, y=None):

    if y is None:

        y = PAGE_HEIGHT - 100  # siempre inicia arriba

    canvas.setFont("Helvetica-Bold", 18)

    canvas.drawString(MARGIN, y, title)

    canvas.line(MARGIN, y - 10, PAGE_WIDTH - MARGIN, y - 10)

    return y - 40


def draw_subsection_title(canvas, text, y):

    canvas.setFont("Helvetica-Bold", 14)

    canvas.drawString(MARGIN, y, text)

    return y - 30


def nueva_pagina_con_titulo(canvas, page_num, project_data, titulo):

    canvas.showPage()

    page_num += 1

    draw_header_footer(
        canvas,
        page_num,
        {
            "logo_sup_izq": project_data["logo_sup_izq"],
            "logo_sup_der": project_data["logo_sup_der"],
            "logo_inf_izq": project_data["logo_inf_izq"],
            "logo_inf_der": project_data["logo_inf_der"],
        },
    )

    cursor_y = PAGE_HEIGHT - 100

    cursor_y = draw_section_title(canvas, titulo, cursor_y)

    return page_num, cursor_y
