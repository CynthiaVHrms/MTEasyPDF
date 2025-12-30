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
        canvas.setFont("Helvetica", 12)
        canvas.drawCentredString(PAGE_WIDTH / 2, 15, str(page_num))


def draw_section_title(canvas, title, y=None):
    if y is None:
        y = PAGE_HEIGHT - 100  # siempre inicia arriba

    # quitar numeración
    clean_title = title.lstrip("0123456789.-_ ").strip()

    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(MARGIN, y, clean_title)
    canvas.line(MARGIN, y - 8, PAGE_WIDTH - MARGIN, y - 8)
    return y - 40



def draw_subsection_title(canvas, text, y):
    canvas.setFont("Helvetica-Bold", 14)
    clean_text = text.lstrip("0123456789.-_ ").strip()
    canvas.drawString(MARGIN, y, clean_text)
    return y - 22


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

def draw_index(canvas, index_items, project_data, start_page=1):
    cursor_y = PAGE_HEIGHT - 120

    # ----- TÍTULO -----
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(MARGIN, cursor_y, "Índice")
    canvas.line(MARGIN, cursor_y - 8, PAGE_WIDTH - MARGIN, cursor_y - 8)
    cursor_y -= 40

    def clean_title(text):
        return text.lstrip("0123456789.- ").strip()

    INDENT_STEP = 18
    RIGHT_GAP = 20  # 🔥 menos espacio antes del número

    for item in index_items:
        level = item["level"]

        # ----- FUENTE POR NIVEL -----
        if level == 1:
            font_size = 14
            line_gap = 22
        elif level == 2:
            font_size = 13
            line_gap = 20
        else:
            font_size = 12
            line_gap = 18

        canvas.setFont("Helvetica", font_size)

        indent = (level - 1) * INDENT_STEP
        title = clean_title(item["title"])
        page_text = str(item["page"] + start_page - 2)

        if cursor_y < 100:
            canvas.showPage()
            # Aquí pasamos project_data correctamente:
            draw_header_footer(canvas, start_page, project_data) 
            cursor_y = PAGE_HEIGHT - 100

        # ----- PUNTOS -----
        text_width = canvas.stringWidth(title, "Helvetica", font_size)
        dot_width = canvas.stringWidth(".", "Helvetica", font_size)

        max_width = PAGE_WIDTH - MARGIN - RIGHT_GAP
        dots_width = max_width - (MARGIN + indent) - text_width
        dot_count = int(dots_width / dot_width)

        dots = "." * max(dot_count, 2)

        canvas.drawString(
            MARGIN + indent,
            cursor_y,
            title + dots
        )

        canvas.drawRightString(
            PAGE_WIDTH - MARGIN,
            cursor_y,
            page_text
        )

        cursor_y -= line_gap 

    canvas.showPage()
    

def draw_introduccion(canvas, texto, start_y=None):
    if start_y is None:
        start_y = PAGE_HEIGHT - 100

    cursor_y = start_y

    # ----- TÍTULO -----
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(MARGIN, cursor_y, "Introducción")
    canvas.line(MARGIN, cursor_y - 8, PAGE_WIDTH - MARGIN, cursor_y - 8)
    cursor_y -= 40

    # ----- TEXTO -----
    canvas.setFont("Helvetica", 11)
    line_height = 16

    for raw_line in texto.split("\n"):
        # Respeta líneas en blanco
        if raw_line.strip() == "":
            cursor_y -= line_height
            continue

        # Salto de página automático
        if cursor_y < 100:
            canvas.showPage()
            draw_header_footer(canvas, None, None)
            cursor_y = PAGE_HEIGHT - 100
            canvas.setFont("Helvetica", 11)

        # Respeta identación manual (espacios)
        canvas.drawString(
            MARGIN,
            cursor_y,
            raw_line
        )
        cursor_y -= line_height

    return cursor_y

