from flask import Blueprint, render_template, request, send_file, redirect, url_for, send_from_directory
import pandas as pd
from .pdf import generar_pdf
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/upload", methods=["GET"])
def upload():
    processed = request.args.get('processed')
    cache_buster = datetime.now().strftime('%Y%m%d%H%M%S')
    return render_template("upload.html", processed=processed, cache_buster=cache_buster)

@main_bp.route("/procesar", methods=["POST"])
def procesar():
    if 'archivo' not in request.files:
        return redirect(url_for('main.upload', error="No se seleccionó ningún archivo."))

    archivo = request.files['archivo']
    if archivo.filename == '':
        return redirect(url_for('main.upload', error="No se seleccionó ningún archivo."))

    try:
        df = pd.read_excel(archivo)

        # Captura el presupuesto mensual desde el formulario
        presupuesto_str = request.form.get('presupuesto', '0')
        presupuesto_mensual = float(presupuesto_str)

        # Limpiar los nombres de las columnas para evitar errores de espacios
        df.columns = df.columns.str.strip()

        # Nuevo: verificar si las columnas existen antes de usarlas
        df['Demanda diaria'] = 0
        df['Stock mínimo'] = 0
        df['Stock seguridad'] = 0
        df['Stock máximo'] = 0
        if 'Ventas Totales' in df.columns and 'Tiempo' in df.columns and 'Reposición (días)' in df.columns:
            df['Demanda diaria'] = df['Ventas Totales'] / df['Tiempo']
            df['Stock mínimo'] = df['Demanda diaria'] * df['Reposición (días)']
            df['Stock seguridad'] = df['Stock mínimo'] * 0.05
            df['Stock máximo'] = df['Stock mínimo'] + df['Stock seguridad']

        # Limpiar nombres de producto si la columna existe
        if 'Nombre Producto' in df.columns:
            df['Nombre Producto'] = df['Nombre Producto'].str.strip().str.lower()
        else:
            df['Nombre Producto'] = "Producto Genérico" # Nombre de respaldo

        # Inicializar variables para estadísticas de ventas y gastos
        total_ventas = 0
        producto_mas_vendido = "N/A"
        producto_menos_vendido = "N/A"
        alerta_presupuesto = ""
        gastos_por_mes = pd.DataFrame(columns=['Mes', 'Gastos'])

        # Procesar datos de ventas si la columna existe
        if 'Ventas' in df.columns and not df['Ventas'].empty:
            total_ventas = df['Ventas'].sum()
            df_ventas = df.groupby('Nombre Producto')['Ventas'].sum().reset_index()
            if not df_ventas.empty:
                producto_mas_vendido = df_ventas.loc[df_ventas['Ventas'].idxmax()]['Nombre Producto']
                producto_menos_vendido = df_ventas.loc[df_ventas['Ventas'].idxmin()]['Nombre Producto']
        
        # Procesar datos de fecha y gastos si las columnas existen
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=False, errors='coerce')
            df['Mes'] = df['Fecha'].dt.strftime('%B %Y')
            
            # Nuevo: cálculo y guardado de ventas por producto
            if 'Ventas' in df.columns:
                df_ventas_mes = df.groupby(['Nombre Producto', 'Mes'])['Ventas'].sum().reset_index()
                df_ventas_mes.to_json("app/static/ventas_por_producto.json", orient='records')

            if 'Gastos(compras)' in df.columns:
                gastos_por_mes = df.groupby('Mes')['Gastos(compras)'].sum().reset_index()
                gastos_por_mes.to_json("app/static/gastos_por_mes.json", orient='records')

                if not gastos_por_mes.empty:
                    total_gastos_actual = gastos_por_mes['Gastos(compras)'].sum()
                    if total_gastos_actual > presupuesto_mensual:
                        alerta_presupuesto = f"¡Alerta! Los gastos totales del mes ({float(total_gastos_actual):.2f}) exceden el presupuesto fijado ({presupuesto_mensual:.2f})."
            else:
                gastos_por_mes = pd.DataFrame(columns=['Mes', 'Gastos'])

            # Crear el resumen mensual de productos solo si la columna 'Fecha' existe
            if 'Stock Final' in df.columns and 'Nombre Producto' in df.columns:
                df_sorted = df.sort_values('Fecha')
                resumen_productos = df_sorted.groupby(['Nombre Producto', 'Mes']).agg(
                    Stock_Final_Ultimo_Dia=('Stock Final', 'last'),
                    Stock_Minimo_Promedio=('Stock mínimo', 'mean'),
                    Stock_Maximo_Promedio=('Stock máximo', 'mean')
                ).reset_index()
            else:
                resumen_productos = pd.DataFrame()
            
            resumen_productos.to_json("app/static/resumen_productos.json", orient='records')

            # Nuevo: Generar gráficos y guardarlos como imágenes
            if 'Stock mínimo' in df.columns and 'Stock máximo' in df.columns and 'Nombre Producto' in df.columns:
                df_grafico = df_sorted.groupby('Nombre Producto').agg({
                    'Stock mínimo': 'mean',
                    'Stock máximo': 'mean'
                }).reset_index()
                
                plt.figure(figsize=(10, 6))
                df_grafico.set_index('Nombre Producto').plot(kind='bar', stacked=True)
                plt.title('Stock Mínimo y Máximo Promedio por Producto')
                plt.ylabel('Cantidad')
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.savefig('app/static/grafico_stock.png')
                plt.close()

            if 'Ventas' in df.columns and 'Nombre Producto' in df.columns:
                df_grafico_ventas = df.groupby('Nombre Producto')['Ventas'].sum().reset_index()
                plt.figure(figsize=(10, 6))
                plt.bar(df_grafico_ventas['Nombre Producto'], df_grafico_ventas['Ventas'], color='skyblue')
                plt.title('Ventas Totales por Producto')
                plt.ylabel('Ventas')
                plt.xlabel('Producto')
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.savefig('app/static/grafico_ventas.png')
                plt.close()

        else:
            with open("app/static/resumen_productos.json", 'w') as f:
                json.dump([], f)
            with open("app/static/gastos_por_mes.json", 'w') as f:
                json.dump([], f)
            with open("app/static/ventas_por_producto.json", 'w') as f:
                json.dump([], f)
        
        # Guardar las estadísticas y la alerta en un archivo JSON para el PDF
        resumen_ventas = {
            'total_ventas': float(total_ventas),
            'producto_mas_vendido': producto_mas_vendido,
            'producto_menos_vendido': producto_menos_vendido,
            'alerta_presupuesto': alerta_presupuesto
        }
        with open("app/static/resumen_ventas.json", 'w') as f:
            json.dump(resumen_ventas, f)

        df.to_excel("app/static/inventario_calculado.xlsx", index=False)
        
        return redirect(url_for('main.upload', processed='True'))

    except Exception as e:
        return render_template("upload.html", error=f"Error al procesar el archivo: {e}"), 500

@main_bp.route("/generar_pdf")
def generar_pdf_route():
    try:
        pdf_stream = generar_pdf()
        # Envía el archivo PDF con los encabezados correctos
        return send_file(
            pdf_stream,
            as_attachment=True,
            download_name='Reporte_Inventario.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        return f"Error al generar el PDF: {e}", 500

@main_bp.route("/dashboard")
def dashboard():
    return "Esta es la página de dashboard"

@main_bp.route("/descargar-plantilla")
def descargar_plantilla():
    return send_from_directory(
        os.path.join(os.getcwd(), 'app', 'static'),
        'Plantilla_Inventario_Usuario.xlsx',
        as_attachment=True
    )