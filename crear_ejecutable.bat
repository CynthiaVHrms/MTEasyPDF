@echo off
echo ====================================================
echo   Generando Ejecutable MT Easy PDF (Versión Final)
echo ====================================================

:: 1. Activar el entorno virtual
call venv\Scripts\activate

:: 2. Limpieza profunda para evitar errores de DLL y archivos temporales
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: 3. Ejecutar PyInstaller
:: --paths ".": Obliga a buscar main.py y pdf_layout.py en la raíz
:: --collect-all: Asegura que librerías pesadas se copien completas
pyinstaller --noconfirm --onedir --windowed --clean ^
 --paths "." ^
 --add-data "Frontend;Frontend" ^
 --add-data "input;input" ^
 --icon "icono.ico" ^
 --name "MTEasyPDF_App" ^
 Frontend/app_gui.py

echo.
echo ====================================================
echo   PROCESO TERMINADO
echo   El ejecutable real esta en: dist/MTEasyPDF_App/
echo ====================================================
pause