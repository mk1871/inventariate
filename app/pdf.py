from io import BytesIO
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt


def generar_pdf():
    # Leer el archivo procesado
    df = pd.read_excel("app/static/inventario_calculado.xlsx")

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
    grafico_path = "app/static/grafico.png"
    plt.savefig(grafico_path)
    plt.close()

    # Crear PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(200, 750, "Reporte de Inventario")
    c.setFont("Helvetica", 12)
    c.drawString(50, 720, f"Fecha: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    c.drawString(50, 700, f"Total de productos: {total_productos}")
    c.drawString(50, 680, f"Stock mínimo total: {stock_min_total:.2f}")
    c.drawString(50, 660, f"Stock máximo total: {stock_max_total:.2f}")
    c.drawString(50, 640, f"Producto de mayor demanda: {producto_mayor_demanda}")
    c.drawImage(grafico_path, 50, 350, width=500, height=300)

    # Tabla
    y_position = 300
    c.drawString(50, y_position, "Producto | Stock Final | Stock Mínimo | Stock Máximo")
    y_position -= 20
    for _, row in df.iterrows():
        c.drawString(50, y_position, f"{row['Producto']} | {row['Stock Final']} | {row['Stock mínimo']:.2f} | {row['Stock máximo']:.2f}")
        y_position -= 15
        if y_position < 50:
            c.showPage()
            y_position = 750

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="inventario_reporte.pdf", mimetype="application/pdf")