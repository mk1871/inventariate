# app/pdf.py

from fpdf import FPDF
import pandas as pd
import json
import os
import io
from flask import session
from .s3_utils import download_file_obj_from_s3
from io import BytesIO


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
        # Obtener información de la sesión desde S3
        session_id = session.get('processing_session')
        bucket_name = session.get('bucket_name')

        if not session_id or not bucket_name:
            raise Exception("No se encontró sesión de procesamiento. Por favor, procesa un archivo primero.")

        # Descargar resumen_ventas.json desde S3
        resumen_content = download_file_obj_from_s3(bucket_name, f"{session_id}/resumen_ventas.json")
        if resumen_content:
            resumen_ventas = json.loads(resumen_content.getvalue().decode('utf-8'))
            generar_graficos_opcion = resumen_ventas.get('generar_graficos', False)
        else:
            resumen_ventas = {
                'total_ventas': 0,
                'producto_mas_vendido': 'N/A',
                'producto_menos_vendido': 'N/A',
                'alerta_presupuesto': ''
            }
            generar_graficos_opcion = False

        # Descargar resumen_productos.json desde S3
        productos_content = download_file_obj_from_s3(bucket_name, f"{session_id}/resumen_productos.json")
        if productos_content:
            df_productos = pd.read_json(BytesIO(productos_content.getvalue()))
        else:
            df_productos = pd.DataFrame(
                columns=['Nombre Producto', 'Mes', 'Stock Final', 'Stock mínimo', 'Stock máximo'])

        # Descargar gastos_por_mes.json desde S3
        gastos_content = download_file_obj_from_s3(bucket_name, f"{session_id}/gastos_por_mes.json")
        if gastos_content:
            df_gastos = pd.read_json(BytesIO(gastos_content.getvalue()))
            df_gastos = df_gastos.rename(columns={'Gastos(compras)': 'Gastos'})
        else:
            df_gastos = pd.DataFrame(columns=['Mes', 'Gastos'])

        # Descargar ventas_por_producto.json desde S3
        ventas_content = download_file_obj_from_s3(bucket_name, f"{session_id}/ventas_por_producto.json")
        if ventas_content:
            df_ventas_mes = pd.read_json(BytesIO(ventas_content.getvalue()))
        else:
            df_ventas_mes = pd.DataFrame(columns=['Nombre Producto', 'Mes', 'Ventas'])

        # Descargar nombres_graficos.json desde S3
        nombres_content = download_file_obj_from_s3(bucket_name, f"{session_id}/nombres_graficos.json")
        if nombres_content:
            nombres_graficos = json.loads(nombres_content.getvalue().decode('utf-8'))
        else:
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

        # Información adicional del resumen
        if 'presupuesto_mensual' in resumen_ventas:
            pdf.cell(200, 10,
                     txt=f"Presupuesto mensual: {format_currency(resumen_ventas.get('presupuesto_mensual', 0))}",
                     ln=True)

        if 'saldo_final' in resumen_ventas:
            saldo_final = resumen_ventas.get('saldo_final', 0)
            color = 0, 0, 0  # Negro por defecto
            if saldo_final < 0:
                color = 255, 0, 0  # Rojo para déficit
            elif saldo_final > 0:
                color = 0, 128, 0  # Verde para superávit

            pdf.set_text_color(*color)
            pdf.cell(200, 10, txt=f"Saldo final: {format_currency(saldo_final)}", ln=True)
            pdf.set_text_color(0, 0, 0)  # Volver a negro

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
                pdf.cell(40, 10, str(int(row.get('Stock_Final_Ultimo_Dia', 0))), 1, 0, 'C')
                pdf.cell(40, 10, f"{row.get('Stock_Minimo_Promedio', 0):.2f}", 1, 0, 'C')
                pdf.cell(40, 10, f"{row.get('Stock_Maximo_Promedio', 0):.2f}", 1, 1, 'C')
        pdf.ln(5)

        # Sección de gráficos (solo si hay gráficos y la opción está activada)
        if generar_graficos_opcion and (nombres_graficos['ventas'] or nombres_graficos['stock']):
            pdf.add_page()
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(200, 10, txt="5. Gráficos", ln=True)
            pdf.ln(10)

            # Descargar y mostrar gráficos de ventas
            for i, nombre in enumerate(nombres_graficos['ventas']):
                try:
                    # Descargar gráfico desde S3
                    grafico_content = download_file_obj_from_s3(bucket_name, f"{session_id}/{nombre}")
                    if grafico_content:
                        # Guardar temporalmente para mostrarlo en el PDF
                        temp_path = f"/tmp/{nombre}"
                        with open(temp_path, 'wb') as f:
                            f.write(grafico_content.getvalue())

                        pdf.image(temp_path, x=10, y=None, w=180)
                        pdf.ln(85)  # Espacio después del gráfico

                        # Limpiar archivo temporal
                        os.remove(temp_path)

                        # Agregar página si hay más gráficos y este no es el último
                        if i < len(nombres_graficos['ventas']) - 1 or nombres_graficos['stock']:
                            pdf.add_page()
                except Exception as e:
                    pdf.cell(200, 10, txt=f"Error al cargar gráfico {nombre}: {str(e)}", ln=True)

            # Descargar y mostrar gráficos de stock
            for i, nombre in enumerate(nombres_graficos['stock']):
                try:
                    # Descargar gráfico desde S3
                    grafico_content = download_file_obj_from_s3(bucket_name, f"{session_id}/{nombre}")
                    if grafico_content:
                        # Guardar temporalmente para mostrarlo en el PDF
                        temp_path = f"/tmp/{nombre}"
                        with open(temp_path, 'wb') as f:
                            f.write(grafico_content.getvalue())

                        pdf.image(temp_path, x=10, y=None, w=180)
                        pdf.ln(85)  # Espacio después del gráfico

                        # Limpiar archivo temporal
                        os.remove(temp_path)

                        # Agregar página si hay más gráficos
                        if i < len(nombres_graficos['stock']) - 1:
                            pdf.add_page()
                except Exception as e:
                    pdf.cell(200, 10, txt=f"Error al cargar gráfico {nombre}: {str(e)}", ln=True)

        # Pie de página con información de la sesión
        pdf.set_y(-15)
        pdf.set_font('Arial', 'I', 8)
        pdf.cell(0, 10, f'Reporte generado el: {session_id}', 0, 0, 'C')

    except Exception as e:
        # En caso de error, crear un PDF con el mensaje de error
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Error al generar el reporte PDF", ln=True)
        pdf.cell(200, 10, txt=f"Detalles: {str(e)}", ln=True)
        pdf.cell(200, 10, txt="Por favor, intenta procesar el archivo nuevamente.", ln=True)

    finally:
        # Generar el PDF final
        pdf_output = pdf.output(dest='S').encode('latin-1')
        return BytesIO(pdf_output)