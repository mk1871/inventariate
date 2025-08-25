from flask import Flask, render_template, request, send_file
import pandas as pd
from io import BytesIO

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'archivo' not in request.files:
        return "No se seleccionó ningún archivo", 400

    archivo = request.files['archivo']
    if archivo.filename == '':
        return "Nombre de archivo vacío", 400

    try:
        # Leer el archivo Excel
        df = pd.read_excel(archivo)

        # Aquí puedes añadir tus cálculos:
        # Ejemplo simple: añadir columnas
        df['Stock Minimo'] = df['Ventas'] / df['Dias'] * df['TiempoReposicion']
        df['Stock Seguridad'] = df['Stock Minimo'] * 0.05
        df['Stock Maximo'] = df['Stock Minimo'] + df['Stock Seguridad']

        # Convertir a Excel para descargar
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        return send_file(output, as_attachment=True,
                         download_name="inventario_procesado.xlsx",
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    except Exception as e:
        return f"Error al procesar el archivo: {e}", 500

if __name__ == '__main__':
    app.run(debug=True)
