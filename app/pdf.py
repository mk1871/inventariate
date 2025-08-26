from fpdf import FPDF
import pandas as pd
import json
import os
import io

def generar_pdf():
    # Cargar datos de los archivos JSON
    try:
        with open("app/static/resumen_ventas.json", 'r') as f:
            resumen_ventas = json.load(f)
    except FileNotFoundError:
        resumen_ventas = {
            'total_ventas': 0,
            'producto_mas_vendido': 'N/A',
            'producto_menos_vendido': 'N/A',
            'alerta_presupuesto': ''
        }

    try:
        df_productos = pd.read_json("app/static/resumen_productos.json")
    except (FileNotFoundError, ValueError):
        df_productos = pd.DataFrame(columns=['Nombre Producto', 'Mes', 'Stock Final', 'Stock mínimo', 'Stock máximo'])

    try:
        df_gastos = pd.read_json("app/static/gastos_por_mes.json")
        df_gastos = df_gastos.rename(columns={'Gastos(compras)': 'Gastos'})
    except (FileNotFoundError, ValueError):
        df_gastos = pd.DataFrame(columns=['Mes', 'Gastos'])

    # Nuevo: Cargar ventas por producto del JSON
    try:
        df_ventas_mes = pd.read_json("app/static/ventas_por_producto.json")
    except (FileNotFoundError, ValueError):
        df_ventas_mes = pd.DataFrame(columns=['Nombre Producto', 'Mes', 'Ventas'])

    # Crear el PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    # Título
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(200, 10, txt="Reporte de Inventario y Finanzas", ln=True, align='C')
    pdf.ln(10)

    # Resumen general
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="1. Resumen General", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Total de ventas: {resumen_ventas['total_ventas']:.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Producto más vendido: {resumen_ventas['producto_mas_vendido']}", ln=True)
    pdf.cell(200, 10, txt=f"Producto menos vendido: {resumen_ventas['producto_menos_vendido']}", ln=True)
    if resumen_ventas['alerta_presupuesto']:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(200, 10, txt=resumen_ventas['alerta_presupuesto'], ln=True)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    # Tabla de ventas por producto y mes
    if not df_ventas_mes.empty:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="2. Ventas por Producto y Mes", ln=True)
        pdf.ln(5)

        pdf.set_fill_color(200, 220, 255)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(60, 10, "Producto", 1, 0, 'C', 1)
        pdf.cell(60, 10, "Mes", 1, 0, 'C', 1)
        pdf.cell(60, 10, "Ventas", 1, 1, 'C', 1)

        pdf.set_font("Arial", '', 10)
        for index, row in df_ventas_mes.iterrows():
            pdf.cell(60, 10, str(row['Nombre Producto']), 1, 0, 'C')
            pdf.cell(60, 10, str(row['Mes']), 1, 0, 'C')
            pdf.cell(60, 10, str(f"{row['Ventas']:.2f}"), 1, 1, 'C')
    pdf.ln(5)

    # Tabla de gastos por mes
    if not df_gastos.empty:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="3. Gastos por Mes", ln=True)
        pdf.ln(5)

        pdf.set_fill_color(200, 220, 255)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(95, 10, "Mes", 1, 0, 'C', 1)
        pdf.cell(95, 10, "Gastos", 1, 1, 'C', 1)

        pdf.set_font("Arial", '', 12)
        for index, row in df_gastos.iterrows():
            pdf.cell(95, 10, str(row['Mes']), 1, 0, 'C')
            pdf.cell(95, 10, str(f"{row['Gastos']:.2f}"), 1, 1, 'C')
    pdf.ln(5)

    # Tabla de resumen de stock
    if not df_productos.empty:
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="4. Resumen de Stock por Producto", ln=True)
        pdf.ln(5)

        pdf.set_fill_color(200, 220, 255)
        pdf.set_font("Arial", 'B', 10)
        pdf.cell(40, 10, "Producto", 1, 0, 'C', 1)
        pdf.cell(30, 10, "Mes", 1, 0, 'C', 1)
        pdf.cell(40, 10, "Stock Final", 1, 0, 'C', 1)
        pdf.cell(40, 10, "Stock Min. Prom.", 1, 0, 'C', 1)
        pdf.cell(40, 10, "Stock Máx. Prom.", 1, 1, 'C', 1)

        pdf.set_font("Arial", '', 10)
        for index, row in df_productos.iterrows():
            pdf.cell(40, 10, str(row['Nombre Producto']), 1, 0, 'C')
            pdf.cell(30, 10, str(row['Mes']), 1, 0, 'C')
            pdf.cell(40, 10, str(f"{row['Stock_Final_Ultimo_Dia']:.2f}"), 1, 0, 'C')
            pdf.cell(40, 10, str(f"{row['Stock_Minimo_Promedio']:.2f}"), 1, 0, 'C')
            pdf.cell(40, 10, str(f"{row['Stock_Maximo_Promedio']:.2f}"), 1, 1, 'C')
    pdf.ln(5)

    # Gráficos
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="5. Gráficos", ln=True)
    pdf.ln(5)
    
    # Incluir el gráfico de ventas
    if os.path.exists('app/static/grafico_ventas.png'):
        pdf.image('app/static/grafico_ventas.png', x=10, y=None, w=180)
        pdf.ln(10)
    
    # Incluir el gráfico de stock
    if os.path.exists('app/static/grafico_stock.png'):
        pdf.image('app/static/grafico_stock.png', x=10, y=None, w=180)
        pdf.ln(10)

    # Guardar PDF en un buffer de memoria
    pdf_output = pdf.output(dest='S').encode('latin-1')
    return io.BytesIO(pdf_output)