import sys
import os

import sys
import os

# Configuración de rutas para PyInstaller
if getattr(sys, 'frozen', False):
    # Si es el ejecutable (.exe)
    base_path = sys._MEIPASS
else:
    # Si es ejecución normal
    base_path = os.path.dirname(os.path.abspath(__file__))

# Añadimos la raíz al PATH para que encuentre main.py y pdf_layout.py
sys.path.append(base_path)

# Ahora sí, importa tus módulos
import main

# 1. Configurar la ruta para encontrar main.py (debe ir ANTES del import de main)
# Obtenemos la ruta absoluta de la carpeta donde está app_gui.py y subimos un nivel
directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_raiz = os.path.dirname(directorio_actual)

if directorio_raiz not in sys.path:
    sys.path.append(directorio_raiz)

# 2. Ahora sí, realizamos las importaciones
import zipfile
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
    QProgressBar,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Importamos la función desde el archivo main.py en la raíz
try:
    from main import main as ejecutar_backend
except ImportError as e:
    print(f"Error: No se pudo encontrar main.py en {directorio_raiz}")
    raise e


# Hilo para que la interfaz no se congele
class WorkerThread(QThread):
    progreso = pyqtSignal(int)
    finalizado = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, data_proyecto):
        super().__init__()
        self.data_proyecto = data_proyecto

    def run(self):
        try:
            # Aquí llamamos a tu función main() pero pasando los datos de la GUI
            # Nota: Necesitarás ajustar un poco tu main.py para recibir estos datos
            resultado = ejecutar_backend(
                self.data_proyecto, callback_progreso=self.progreso.emit
            )
            self.finalizado.emit(resultado)
        except Exception as e:
            self.error.emit(str(e))


class MemoriaApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generador de Memoria Técnica - Hemac")
        self.setMinimumWidth(1000)
        self.setStyleSheet(self.base_styles())
        self.init_ui()

    def init_ui(self):
        layout_principal = QVBoxLayout()

        title = QLabel("MT Easy PDF")
        title.setObjectName("AppTitle")
        layout_principal.addWidget(title, alignment=Qt.AlignHCenter)

        # --- Contenedor de Formulario ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        form_layout = QVBoxLayout(container)

        # Campos (usando tus nombres originales)
        self.titulo = QLineEdit()
        self.info_extra = QTextEdit()
        self.introduccion = QTextEdit()
        self.zip_file = QLineEdit()
        self.portada_img = QLineEdit()
        self.logo_sup_der = QLineEdit()
        self.logo_sup_izq = QLineEdit()
        self.logo_inf_der = QLineEdit()
        self.logo_inf_izq = QLineEdit()
        self.output_folder = QLineEdit()

        # Secciones
        form_layout.addWidget(self.section_title("Información General"))
        form_layout.addLayout(self._row("Título del Proyecto *", self.titulo))
        form_layout.addLayout(
            self._row("Información Extra (Subtítulo)", self.info_extra)
        )
        form_layout.addLayout(self._row("Introducción *", self.introduccion))

        form_layout.addWidget(self.section_title("Archivos y Logos"))
        form_layout.addLayout(
            self._file_row("Archivo ZIP de Evidencias *", self.zip_file)
        )
        form_layout.addLayout(self._file_row("Imagen de Portada", self.portada_img))
        form_layout.addLayout(
            self._file_row("Logo Superior Izquierdo *", self.logo_sup_izq)
        )
        form_layout.addLayout(
            self._file_row("Logo Superior Derecho *", self.logo_sup_der)
        )
        form_layout.addLayout(
            self._file_row("Logo Inferior Izquierdo", self.logo_inf_izq)
        )
        form_layout.addLayout(
            self._file_row("Logo Inferior Derecho", self.logo_inf_der)
        )

        form_layout.addWidget(self.section_title("Configuración de Salida"))
        form_layout.addLayout(
            self._directory_row(
                "Carpeta donde se guardará el ZIP *", self.output_folder
            )
        )

        scroll.setWidget(container)
        layout_principal.addWidget(scroll)

        # --- Barra de Progreso ---
        self.pbar = QProgressBar()
        self.pbar.setVisible(False)
        self.pbar.setTextVisible(True)
        self.pbar.setStyleSheet("QProgressBar { height: 20px; border-radius: 5px; }")
        layout_principal.addWidget(self.pbar)

        # --- Botón Generar ---
        self.btn_generar = QPushButton("Generar Memoria Técnica")
        self.btn_generar.setObjectName("PrimaryButton")
        self.btn_generar.clicked.connect(self.iniciar_proceso)
        layout_principal.addWidget(self.btn_generar)

        self.setLayout(layout_principal)

    def section_title(self, text):
        lbl = QLabel(text)
        lbl.setObjectName("SectionTitle")
        return lbl

    def _row(self, label, widget):
        l = QVBoxLayout()
        l.addWidget(QLabel(label))
        l.addWidget(widget)
        return l

    def _file_row(self, label, field):
        l = QVBoxLayout()
        l.addWidget(QLabel(label))
        h = QHBoxLayout()
        h.addWidget(field)
        btn = QPushButton("Buscar")
        btn.setObjectName("SecondaryButton")
        btn.clicked.connect(lambda: self.select_file(field))
        h.addWidget(btn)
        l.addLayout(h)
        return l

    def select_file(self, target):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar archivo")
        if path:
            target.setText(path)
            
    def _directory_row(self, label, field):
        """Crea una fila con etiqueta, campo de texto y botón para seleccionar carpetas."""
        layout_v = QVBoxLayout()
        layout_v.addWidget(QLabel(label))
        layout_h = QHBoxLayout()
        layout_h.addWidget(field)
        
        btn = QPushButton("Seleccionar")
        btn.setObjectName("SecondaryButton")
        btn.clicked.connect(lambda: self.select_directory(field))
        
        layout_h.addWidget(btn)
        layout_v.addLayout(layout_h)
        return layout_v

    def select_directory(self, target):
        """Abre el diálogo para seleccionar una carpeta y actualiza el campo de texto."""
        path = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de destino")
        if path:
            target.setText(path)

    # Cambiamos el nombre para evitar caracteres especiales como tildes
    def finalizar_proceso(self, ruta_zip):
        self.btn_generar.setEnabled(True)
        self.pbar.setValue(100)
        QMessageBox.information(
            self, "Éxito", f"Memoria generada correctamente en:\n{ruta_zip}"
        )
        # Abre la carpeta donde se guardó el archivo
        if os.path.exists(ruta_zip):
            os.startfile(os.path.dirname(ruta_zip))

    def iniciar_proceso(self):
        # 1. Lista de validación estricta
        obligatorios = [
            (self.titulo.text(), "Título"),
            (self.introduccion.toPlainText(), "Introducción"),
            (self.zip_file.text(), "ZIP de Evidencias"),
            (self.logo_sup_izq.text(), "Logo Superior Izquierdo"),
            (self.logo_sup_der.text(), "Logo Superior Derecho"),
            (self.output_folder.text(), "Carpeta de Salida")
        ]

        for valor, nombre in obligatorios:
            if not valor or valor.strip() == "":
                QMessageBox.warning(self, "Faltan Datos", f"El campo '{nombre}' es obligatorio.")
                return

        # 2. Recolectar datos
        data = {
            "titulo": self.titulo.text(),
            "info_extra": self.info_extra.toPlainText(),
            "introduccion": self.introduccion.toPlainText(),
            "zip_path": self.zip_file.text(),
            "output_dir": self.output_folder.text(),
            "imagen_portada": self.portada_img.text(),
            "logo_sup_izq": self.logo_sup_izq.text(),
            "logo_sup_der": self.logo_sup_der.text(),
            "logo_inf_izq": self.logo_inf_izq.text(),
            "logo_inf_der": self.logo_inf_der.text(),
        }

        self.btn_generar.setEnabled(False)
        self.pbar.setVisible(True)
        self.pbar.setValue(0)

        # Iniciar hilo
        self.worker = WorkerThread(data)
        self.worker.progreso.connect(self.pbar.setValue)
        self.worker.finalizado.connect(self.finalizar_proceso)
        self.worker.error.connect(self.error_proceso)
        self.worker.start()

    def finalizar_proceso(self, ruta_zip):
        self.btn_generar.setEnabled(True)
        QMessageBox.information(
            self, "Éxito", f"Memoria generada correctamente:\n{ruta_zip}"
        )
        # Abrir la carpeta contenedora
        os.startfile(os.path.dirname(ruta_zip))

    def error_proceso(self, mensaje):
        self.btn_generar.setEnabled(True)
        QMessageBox.critical(self, "Error en Proceso", mensaje)

    def base_styles(self):
        return """
        QWidget { background-color: #0D1B2A; color: white; font-family: 'Segoe UI'; font-size: 13px; }
        #AppTitle { font-size: 24px; font-weight: bold; color: #00A9CE; padding: 10px; }
        #SectionTitle { color: #0FF0FC; font-weight: bold; font-size: 16px; margin-top: 15px; border-bottom: 1px solid #1B263B; }
        QLineEdit, QTextEdit { background: #1B263B; border: 1px solid #415A77; border-radius: 4px; padding: 5px; color: white; }
        QPushButton#PrimaryButton { background: #00A9CE; font-weight: bold; height: 40px; border-radius: 5px; margin-top: 10px; }
        QPushButton#PrimaryButton:hover { background: #008eb0; }
        QPushButton#SecondaryButton { background: #415A77; border-radius: 4px; padding: 5px 15px; }
        QProgressBar { border: 2px solid #415A77; border-radius: 5px; text-align: center; }
        QProgressBar::chunk { background-color: #00A9CE; }
        """


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MemoriaApp()
    window.show()
    sys.exit(app.exec_())
