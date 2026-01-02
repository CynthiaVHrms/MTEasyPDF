import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 40

def draw_cover(canvas, data, project_data):
    """
    Dibuja la portada del documento.
    """
    # Fondo de la portada
    canvas.setFillColorRGB(0.95, 0.95, 0.95)
    canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, fill=1, stroke=0)

    # Imagen central
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

    # Títulos
    canvas.setFillColorRGB(0, 0, 0)
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 140, data.get("titulo", ""))

    canvas.setFont("Helvetica", 14)
    canvas.drawCentredString(
        PAGE_WIDTH / 2, PAGE_HEIGHT - 180, data.get("info_extra", "")
    )

    # Dibuja logos, pero el número de página se omite internamente 
    # porque draw_header_footer detectará que es la página 1.
    draw_header_footer(canvas, None, project_data)

    # Finaliza la página de portada e incrementa el contador del canvas a 2
    canvas.showPage()

def draw_header_footer(canvas, page_num, data):
    actual_p = canvas.getPageNumber()
    logo_size = 40
    padding = 20

    # Logos
    for key in ["logo_sup_izq", "logo_sup_der", "logo_inf_izq", "logo_inf_der"]:
        if data.get(key) and os.path.exists(data[key]):
            # Posicionamiento simplificado para mantener el diseño original
            if "sup_izq" in key: x, y = padding, PAGE_HEIGHT - logo_size - padding
            elif "sup_der" in key: x, y = PAGE_WIDTH - logo_size - padding, PAGE_HEIGHT - logo_size - padding
            elif "inf_izq" in key: x, y = padding, padding
            else: x, y = PAGE_WIDTH - logo_size - padding, padding
            
            canvas.drawImage(data[key], x, y, width=logo_size, height=logo_size, mask="auto")

    # Si se requiere número, se dibuja
    if actual_p > 1: 
        canvas.setFont("Helvetica", 12)
        canvas.drawCentredString(PAGE_WIDTH / 2, 15, str(actual_p))

def draw_section_title(canvas, title, y=None):
    if y is None:
        y = PAGE_HEIGHT - 100
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

def nueva_pagina_con_titulo(canvas, project_data, titulo):

    canvas.showPage()
    # Obtenemos el número real del sistema
    actual_p = canvas.getPageNumber()
    
    draw_header_footer(canvas, actual_p, project_data)

    cursor_y = PAGE_HEIGHT - 100
    cursor_y = draw_section_title(canvas, titulo, cursor_y)
    return cursor_y # Solo devuelve el cursor

def draw_index(canvas, index_items, project_data):
    cursor_y = PAGE_HEIGHT - 120
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(MARGIN, cursor_y, "Índice")
    canvas.line(MARGIN, cursor_y - 8, PAGE_WIDTH - MARGIN, cursor_y - 8)
    cursor_y -= 40

    def clean_title_idx(text):
        return text.lstrip("0123456789.- ").strip()

    INDENT_STEP = 18
    RIGHT_GAP = 20

    for item in index_items:
        level = item["level"]
        if level == 1: font_size, line_gap = 14, 24 # Un poco más de aire
        elif level == 2: font_size, line_gap = 13, 20
        else: font_size, line_gap = 12, 18

        if cursor_y < 100:
            canvas.showPage()
            # IMPORTANTE: draw_header_footer ya usa canvas.getPageNumber() internamente
            draw_header_footer(canvas, None, project_data) 
            cursor_y = PAGE_HEIGHT - 120 # Reset de altura tras encabezado
            canvas.setFont("Helvetica-Bold", 20)
            canvas.drawString(MARGIN, cursor_y, "Índice") # Opcional: subtítulo
            cursor_y -= 40

        canvas.setFont("Helvetica", font_size)
        indent = (level - 1) * INDENT_STEP
        title = clean_title_idx(item["title"])
        page_text = str(item["page"])

        text_width = canvas.stringWidth(title, "Helvetica", font_size)
        page_val_width = canvas.stringWidth(page_text, "Helvetica", font_size)
        
        # Calculamos los puntos de forma que no se encimen con el número
        max_dots_x = PAGE_WIDTH - MARGIN - page_val_width - 5
        dots_area_width = max_dots_x - (MARGIN + indent + text_width + 5)
        
        dot_char_width = canvas.stringWidth(".", "Helvetica", font_size)
        num_dots = int(dots_area_width / dot_char_width)
        dots = "." * max(num_dots, 0)

        canvas.drawString(MARGIN + indent, cursor_y, title)
        canvas.drawString(MARGIN + indent + text_width + 5, cursor_y, dots)
        canvas.drawRightString(PAGE_WIDTH - MARGIN, cursor_y, page_text)
        cursor_y -= line_gap 

    # IMPORTANTE: Solo saltamos página al final del índice
    canvas.showPage()

def draw_introduccion(canvas, texto, project_data, start_y=None):
    """
    MODIFICADO: Ahora recibe project_data para los logos si hay salto de página.
    """
    if start_y is None:
        start_y = PAGE_HEIGHT - 100
    cursor_y = start_y

    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(MARGIN, cursor_y, "Introducción")
    canvas.line(MARGIN, cursor_y - 8, PAGE_WIDTH - MARGIN, cursor_y - 8)
    cursor_y -= 40

    canvas.setFont("Helvetica", 11)
    line_height = 16

    for raw_line in texto.split("\n"):
        if raw_line.strip() == "":
            cursor_y -= line_height
            continue

        if cursor_y < 100:
            canvas.showPage()
            # El número se pide al canvas automáticamente
            draw_header_footer(canvas, canvas.getPageNumber(), project_data)
            cursor_y = PAGE_HEIGHT - 100
            canvas.setFont("Helvetica", 11)

        canvas.drawString(MARGIN, cursor_y, raw_line)
        cursor_y -= line_height

    return cursor_y