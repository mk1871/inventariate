from flask import Flask, render_template, request, send_file
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)

# Ruta principal
@app.route('/')
def home():
    return render_template('index.html')

# Ruta para procesar el archivo Excel
@app.route('/procesar', methods=['POST'])
def procesar():
    if 'archivo' not in request.files:
        return "No se seleccionó ningún archivo", 400

    archivo = request.files['archivo']
    if archivo.filename == '':
        return "No se seleccionó ningún archivo", 400

    try:
        # Leer archivo Excel
        df = pd.read_excel(archivo)

        # Calcular columnas (ejemplo con stock mínimo y máximo)
        df['Demanda diaria'] = df['Ventas'] / df['Días']
        df['Stock mínimo'] = df['Demanda diaria'] * df['Tiempo_reposicion']
        df['Stock seguridad'] = df['Stock mínimo'] * 0.05
        df['Stock máximo'] = df['Stock mínimo'] + df['Stock seguridad']

        # Guardar archivo Excel procesado temporalmente
        output_excel = "static/inventario_calculado.xlsx"
        df.to_excel(output_excel, index=False)

        return render_template('resultado.html')

    except Exception as e:
        return f"Error al procesar el archivo: {e}", 500

# NUEVA RUTA: Generar PDF
@app.route('/generar_pdf')
def generar_pdf():
    try:
        # Leer el archivo procesado
        df = pd.read_excel("static/inventario_calculado.xlsx")

        # Estadísticas
        total_productos = len(df)
        stock_min_total = df['Stock mínimo'].sum()
        stock_max_total = df['Stock máximo'].sum()
        producto_mayor_demanda = df.loc[df['Demanda diaria'].idxmax(), 'Producto']

        # Generar gráfico
        plt.figure(figsize=(8, 5))
        plt.bar(df['Producto'], df['Stock mínimo'], label='Stock mínimo')
        plt.bar(df['Producto'], df['Stock máximo'], label='Stock máximo', alpha=0.7)
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        grafico_path = "static/grafico.png"
        plt.savefig(grafico_path)
        plt.close()

        # Crear PDF
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(200, 750, "Reporte de Inventario")
        c.setFont("Helvetica", 12)
        c.drawString(50, 720, f"Fecha: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
        c.drawString(50, 700, f"Total productos: {total_productos}")
        c.drawString(50, 680, f"Stock mínimo total: {round(stock_min_total, 2)}")
        c.drawString(50, 660, f"Stock máximo total: {round(stock_max_total, 2)}")
        c.drawString(50, 640, f"Producto mayor demanda: {producto_mayor_demanda}")

        # Agregar gráfico
        c.drawImage(grafico_path, 50, 400, width=500, height=200)

        c.showPage()
        c.save()

        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="reporte_inventario.pdf", mimetype='application/pdf')

    except Exception as e:
        return f"Error al generar el PDF: {e}", 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8000)
