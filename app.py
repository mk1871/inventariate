from flask import Flask, render_template, request, send_from_directory, send_file
from werkzeug.utils import secure_filename
import pandas as pd
from io import BytesIO
import os

app = Flask(__name__)

# Extensiones permitidas
allowed_extensions = {'xlsx', 'xls'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# RUTA: Página de inicio
@app.route('/')
def home():
    return render_template('index.html')

# RUTA: Página para subir Excel
"""@app.route('/subir')
def subir_excel():
    return render_template('upload.html')"""
@app.route('/upload')  # 👈 Esta es la RUTA
def subir_archivo():   # 👈 Esta es la FUNCIÓN
    return render_template('upload.html')

# RUTA: Página del inventario
@app.route('/inventario')
def inventario():
    return render_template('inventario.html')

# RUTA: Página de login
@app.route('/login')
def login():
    return render_template('login.html')

# RUTA: Descargar plantilla
@app.route('/descargar-plantilla')
def descargar_plantilla():
    try:
        return send_from_directory(
            directory='static',
            path='Plantilla_Inventario_Usuario.xlsx',
            as_attachment=True,
            download_name='Plantilla_Inventario_Usuario.xlsx'
        )
    except Exception as e:
        return f"Error al descargar la plantilla: {e}", 500

# RUTA: Procesar archivo Excel
@app.route('/procesar', methods=['POST'])
def procesar():
    if 'archivo' not in request.files:
        return "No se seleccionó ningún archivo", 400

    archivo = request.files['archivo']
    if archivo.filename == '':
        return "No se seleccionó ningún archivo", 400

    if not allowed_file(archivo.filename):
        return "Tipo de archivo no permitido. Solo se permiten archivos Excel (.xlsx, .xls)", 400

    try:
        df = pd.read_excel(archivo)

        columnas_requeridas = [
            'ID Producto', 'Nombre Producto', 'Stock Inicial', 'Entradas', 'Salidas',
            'Ventas Totales', 'Stock Final', 'Tiempo', 'Reposición (días)'
        ]
        if not all(col in df.columns for col in columnas_requeridas):
            return "El archivo debe contener las columnas requeridas correctamente.", 400

        # Cálculos de inventario
        df['Demanda Diaria'] = df['Ventas Totales'] / df['Tiempo']
        df['Stock Mínimo'] = df['Demanda Diaria'] * df['Reposición (días)']
        df['Stock de Seguridad'] = df['Stock Mínimo'] * 0.05
        df['Stock Mínimo Total'] = df['Stock Mínimo'] + df['Stock de Seguridad']

        # Guardar archivo Excel en memoria
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name="inventario_calculado.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        return f"Error al procesar el archivo: {e}", 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8000)
