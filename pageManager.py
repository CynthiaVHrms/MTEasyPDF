from reportlab.lib.pagesizes import A4
from pdf_layout import draw_header_footer, draw_section_title

PAGE_WIDTH, PAGE_HEIGHT = A4

class PageManager:
    def __init__(self, canvas, project_data):
        self.canvas = canvas
        self.project_data = project_data
        self.page_num = 0
        self.cursor_y = PAGE_HEIGHT - 100

    def new_page(self, with_title=None):
        self.canvas.showPage()
        self.page_num += 1

        draw_header_footer(
            self.canvas,
            self.page_num,
            self.project_data
        )

        self.cursor_y = PAGE_HEIGHT - 100

        if with_title:
            self.cursor_y = draw_section_title(
                self.canvas,
                with_title,
                self.cursor_y
            )

        return self.cursor_y

    def ensure_space(self, needed_height, section_title=None):
        if self.cursor_y - needed_height < 100:
            self.new_page(with_title=section_title)
