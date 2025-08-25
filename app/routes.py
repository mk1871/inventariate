from flask import Blueprint, render_template, request, send_file, redirect, url_for, send_from_directory
import pandas as pd
from .pdf import generar_pdf

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/upload")
def upload():
    return render_template("upload.html")

@main_bp.route("/procesar", methods=["POST"])
def procesar():
    if 'archivo' not in request.files:
        return "No se seleccionó ningún archivo", 400

    archivo = request.files['archivo']
    if archivo.filename == '':
        return "No se seleccionó ningún archivo", 400

    try:
        # Leer archivo Excel
        df = pd.read_excel(archivo)

        # Calcular columnas (stock mínimo y máximo)
        df['Demanda diaria'] = df['Ventas'] / df['Días']
        df['Stock mínimo'] = df['Demanda diaria'] * df['Tiempo_reposicion']
        df['Stock seguridad'] = df['Stock mínimo'] * 0.05
        df['Stock máximo'] = df['Stock mínimo'] + df['Stock seguridad']

        # Guardar archivo Excel procesado
        output_excel = "app/static/inventario_calculado.xlsx"
        df.to_excel(output_excel, index=False)

        return render_template("resultado.html")

    except Exception as e:
        return f"Error al procesar el archivo: {e}", 500


@main_bp.route("/generar_pdf")
def generar_pdf_route():
    try:
        return generar_pdf()
    except Exception as e:
        return f"Error al generar el PDF: {e}", 500

@main_bp.route("/dashboard")
def dashboard():
    return "Esta es la página de dashboard"

# --- NUEVO CÓDIGO ---
@main_bp.route("/descargar-plantilla")
def descargar_plantilla():
    # El archivo Plantilla_Inventario_Usuario.xlsx está en la carpeta raíz del proyecto,
    # pero como el usuario lo subió, se considera parte de los archivos del proyecto.
    # Usaremos una forma para que Flask lo envíe correctamente.
    return send_from_directory(directory='.', path='Plantilla_Inventario_Usuario.xlsx - Hoja1.csv', as_attachment=True)