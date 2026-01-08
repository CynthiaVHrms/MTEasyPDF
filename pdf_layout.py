import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader

from file_engine import (
    limpiar_nombre,
)

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
    canvas.drawCentredString(PAGE_WIDTH / 2, PAGE_HEIGHT - 200, data.get("titulo", ""))

    canvas.setFont("Helvetica", 14)
    canvas.drawCentredString(
        PAGE_WIDTH / 2, PAGE_HEIGHT - 240, data.get("info_extra", "")
    )

    # Dibuja logos, pero el número de página se omite internamente 
    # porque draw_header_footer detectará que es la página 1.
    draw_header_footer(canvas, None, project_data)

    # Finaliza la página de portada e incrementa el contador del canvas a 2
    canvas.showPage()

def draw_header_footer(canvas, page_num, data):
    actual_p = canvas.getPageNumber()
    max_height = 50  # El alto máximo que deseas
    padding = 20

    for key in ["logo_sup_izq", "logo_sup_der", "logo_inf_izq", "logo_inf_der"]:
        path = data.get(key)
        if path and os.path.exists(path):
            # 1. Leer la imagen y obtener dimensiones originales
            img = ImageReader(path)
            orig_w, orig_h = img.getSize()
            
            # 2. Calcular el ancho proporcional basado en el alto deseado (50)
            aspect_ratio = orig_w / orig_h
            calc_width = max_height * aspect_ratio
            
            # 3. Posicionamiento dinámico basado en el nuevo ancho
            if "sup_izq" in key: 
                x, y = padding, PAGE_HEIGHT - max_height - padding
            elif "sup_der" in key: 
                x, y = PAGE_WIDTH - calc_width - padding, PAGE_HEIGHT - max_height - padding
            elif "inf_izq" in key: 
                x, y = padding, padding
            else: # inf_der
                x, y = PAGE_WIDTH - calc_width - padding, padding
            
            # 4. Dibujar con las dimensiones calculadas
            canvas.drawImage(img, x, y, width=calc_width, height=max_height, mask="auto")

    # Número de página
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
    if start_y is None:
        start_y = PAGE_HEIGHT - 100
    cursor_y = start_y

    # Título
    canvas.setFont("Helvetica-Bold", 18)
    canvas.drawString(MARGIN, cursor_y, "Introducción")
    canvas.line(MARGIN, cursor_y - 8, PAGE_WIDTH - MARGIN, cursor_y - 8)
    cursor_y -= 40

    # Configuración de estilos optimizada
    styles = getSampleStyleSheet()
    estilo_intro = ParagraphStyle(
        'IntroStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=18,           # Mayor interlineado (antes 14)
        alignment=0,           # 0=Izquierda (mejor para listas), 4=Justificado
        leftIndent=30,         # Mayor margen a la izquierda (antes 0)
        rightIndent=10,        # Un poco de margen a la derecha
        spaceBefore=12,
        wordWrap='LTR',        # Asegura el envoltorio de palabras estándar
    )

    # PROCESAMIENTO CLAVE: 
    # 1. Reemplazamos espacios iniciales por espacios de no ruptura (&nbsp;) para la indentación
    # 2. Reemplazamos \n por <br/> para saltos de línea
    lineas = []
    for line in texto.split('\n'):
        # Preserva espacios al inicio de la línea para indentar listas
        espacios_iniciales = len(line) - len(line.lstrip())
        linea_formateada = ('&nbsp;' * espacios_iniciales * 2) + line.lstrip()
        lineas.append(linea_formateada)
    
    texto_final = "<br/>".join(lineas)
    p = Paragraph(texto_final, estilo_intro)

    # Dibujado con cálculo de altura
    ancho_disponible = PAGE_WIDTH - (MARGIN * 2) - 30 # Restamos el leftIndent
    w, h = p.wrap(ancho_disponible, cursor_y - 50)
    
    # Dibujamos en la posición calculada
    p.drawOn(canvas, MARGIN, cursor_y - h)
    
    return cursor_y - h - 30


def render_documentacion_links(canvas, cursor_y, pdf_tree, project_data, index=None):
    canvas.showPage()
    draw_header_footer(canvas, canvas.getPageNumber(), project_data)
    
    # 1. Espacio superior compacto
    cursor_y = PAGE_HEIGHT - 100 
    cursor_y = draw_section_title(canvas, "Documentación Técnica", cursor_y)
    
    if index:
        index.add("Documentación Técnica", canvas.getPageNumber(), level=1)
    
    # Pegamos el primer encabezado al título principal
    cursor_y -= 5 

    for seccion, subsecciones in pdf_tree.items():
        # Verificación de contenido
        tiene_pdfs = any(
            pdf_list 
            for sub in subsecciones.values() 
            for grupo in sub.values() 
            for pdf_list in grupo.values() 
            if pdf_list
        )
        
        if not tiene_pdfs:
            continue
        
        # 2. Limpieza de nombre de sección (quitando números como "04 ")
        seccion_aux = limpiar_nombre(seccion)
        # Si limpiar_nombre no quita los números, lo hacemos manualmente:
        import re
        seccion_limpia = re.sub(r'^\d+\s*', '', seccion_aux).strip()

        canvas.setFont("Helvetica-Bold", 12)
        canvas.setFillColorRGB(0.2, 0.4, 0.6)
        canvas.drawString(MARGIN, cursor_y, f"Archivos de: {seccion_limpia}")
        canvas.setFillColor("black")
        
        # 3. Más espacio entre el encabezado azul y la lista
        cursor_y -= 25 

        for subseccion, grupos in subsecciones.items():
            for grupo, categorias in grupos.items():
                for categoria, pdfs in categorias.items():
                    for pdf_path in pdfs:
                        # Control de salto de página
                        if cursor_y < 120:
                            canvas.showPage()
                            draw_header_footer(canvas, canvas.getPageNumber(), project_data)
                            cursor_y = PAGE_HEIGHT - 100
                        
                        # DEFINICIÓN CLAVE
                        nombre_archivo = os.path.basename(pdf_path)
                        
                        # Limpieza de textos de origen
                        sub_l = re.sub(r'^\d+\s*', '', limpiar_nombre(subseccion)).strip()
                        gru_l = re.sub(r'^\d+\s*', '', limpiar_nombre(grupo)).strip()
                        origen = f"{sub_l} > {gru_l}" if grupo else sub_l
                        
                        # Dibujo del elemento
                        canvas.setFont("Helvetica", 11)
                        canvas.setFillColor("blue")
                        canvas.drawString(MARGIN + 20, cursor_y, f"• {nombre_archivo}")
                        
                        canvas.setFont("Helvetica-Oblique", 8)
                        canvas.setFillColorRGB(0.5, 0.5, 0.5)
                        canvas.drawRightString(PAGE_WIDTH - MARGIN, cursor_y, origen)
                        
                        # Link (nombre_archivo ya está definido arriba)
                        canvas.linkURL(f"anexos/{nombre_archivo}", 
                                       (MARGIN, cursor_y - 2, PAGE_WIDTH - MARGIN, cursor_y + 12))
                        
                        canvas.setFillColor("black")
                        # 4. Espaciado entre links aumentado
                        cursor_y -= 22 
        
        # Espacio tras terminar una sección completa
        cursor_y -= 10
        
    return cursor_y