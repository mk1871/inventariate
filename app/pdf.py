# app/pdf.py

from fpdf import FPDF
import pandas as pd
import json
import os
import io

def format_currency(value):
    """
    Formatea un número como moneda con separadores de miles y signo de pesos.
    """
    if value is None:
        return "$0"
    value = int(round(value))
    return f"${value:,}".replace(",", ".")

def generar_pdf():
    try:
        with open("app/static/resumen_ventas.json", 'r') as f:
            resumen_ventas = json.load(f)
        generar_graficos_opcion = resumen_ventas.get('generar_graficos', False)
    except FileNotFoundError:
        resumen_ventas = {
            'total_ventas': 0,
            'producto_mas_vendido': 'N/A',
            'producto_menos_vendido': 'N/A',
            'alerta_presupuesto': ''
        }
        generar_graficos_opcion = False

    try:
        df_productos = pd.read_json("app/static/resumen_productos.json")
    except (FileNotFoundError, ValueError):
        df_productos = pd.DataFrame(columns=['Nombre Producto', 'Mes', 'Stock Final', 'Stock mínimo', 'Stock máximo'])

    try:
        df_gastos = pd.read_json("app/static/gastos_por_mes.json")
        df_gastos = df_gastos.rename(columns={'Gastos(compras)': 'Gastos'})
    except (FileNotFoundError, ValueError):
        df_gastos = pd.DataFrame(columns=['Mes', 'Gastos'])

    try:
        df_ventas_mes = pd.read_json("app/static/ventas_por_producto.json")
    except (FileNotFoundError, ValueError):
        df_ventas_mes = pd.DataFrame(columns=['Nombre Producto', 'Mes', 'Ventas'])
    
    try:
        with open("app/static/nombres_graficos.json", 'r') as f:
            nombres_graficos = json.load(f)
    except FileNotFoundError:
        nombres_graficos = {"stock": [], "ventas": []}

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    pdf.set_font("Arial", 'B', 20)
    pdf.cell(200, 10, txt="Reporte de Inventario y Finanzas", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="1. Resumen General", ln=True)
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Total de ventas: {format_currency(resumen_ventas.get('total_ventas', 0))}", ln=True)
    pdf.cell(200, 10, txt=f"Producto más vendido: {resumen_ventas.get('producto_mas_vendido', 'N/A')}", ln=True)
    pdf.cell(200, 10, txt=f"Producto menos vendido: {resumen_ventas.get('producto_menos_vendido', 'N/A')}", ln=True)
    if resumen_ventas.get('alerta_presupuesto'):
        pdf.set_text_color(255, 0, 0)
        pdf.cell(200, 10, txt=resumen_ventas['alerta_presupuesto'], ln=True)
        pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

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
            pdf.cell(60, 10, str(row.get('Nombre Producto', 'N/A')), 1, 0, 'C')
            pdf.cell(60, 10, str(row.get('Mes', 'N/A')), 1, 0, 'C')
            pdf.cell(60, 10, str(format_currency(row.get('Ventas', 0))), 1, 1, 'C')
    pdf.ln(5)

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
            pdf.cell(95, 10, str(row.get('Mes', 'N/A')), 1, 0, 'C')
            pdf.cell(95, 10, str(format_currency(row.get('Gastos', 0))), 1, 1, 'C')
    pdf.ln(5)

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
            pdf.cell(40, 10, str(row.get('Nombre Producto', 'N/A')), 1, 0, 'C')
            pdf.cell(30, 10, str(row.get('Mes', 'N/A')), 1, 0, 'C')
            pdf.cell(40, 10, str(format_currency(row.get('Stock_Final_Ultimo_Dia', 0))), 1, 0, 'C')
            pdf.cell(40, 10, str(format_currency(row.get('Stock_Minimo_Promedio', 0))), 1, 0, 'C')
            pdf.cell(40, 10, str(format_currency(row.get('Stock_Maximo_Promedio', 0))), 1, 1, 'C')
    pdf.ln(5)
    
    if generar_graficos_opcion and (nombres_graficos['ventas'] or nombres_graficos['stock']):
        pdf.add_page()
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(200, 10, txt="5. Gráficos", ln=True)
        pdf.ln(5)
        
        for nombre in nombres_graficos['ventas']:
            path = os.path.join('app', 'static', nombre)
            if os.path.exists(path):
                pdf.image(path, x=10, y=None, w=180)
                pdf.ln(10)
        
        for nombre in nombres_graficos['stock']:
            path = os.path.join('app', 'static', nombre)
            if os.path.exists(path):
                pdf.image(path, x=10, y=None, w=180)
                pdf.ln(10)

    pdf_output = pdf.output(dest='S').encode('latin-1')
    return io.BytesIO(pdf_output)