from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generar_pdf():
    c = canvas.Canvas("prueba.pdf", pagesize=A4)
    width, height = A4

    c.setFont("Helvetica", 16)
    c.drawString(50, height - 50, "Generador de Reportes - MVP")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 100, "Si ves este PDF, el proyecto va bien.")

    c.showPage()
    c.save()

if __name__ == "__main__":
    generar_pdf()
