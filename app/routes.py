from flask import Blueprint, render_template, request, send_file, redirect, url_for, send_from_directory
import pandas as pd
from .pdf import generar_pdf
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt
plt.switch_backend('Agg')

main_bp = Blueprint('main', __name__)

def format_currency_string(value):
    """
    Formatea un número como moneda con separadores de miles y signo de pesos.
    """
    if value is None:
        return "$0"
    value = int(round(value))
    return f"${value:,}".replace(",", ".")

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

        presupuesto_str = request.form.get('presupuesto', '0')
        presupuesto_mensual = float(presupuesto_str)
        
        generar_graficos = 'generar_graficos' in request.form

        df.columns = df.columns.str.strip()
        df['Demanda diaria'] = 0
        df['Stock mínimo'] = 0
        df['Stock seguridad'] = 0
        df['Stock máximo'] = 0
        if 'Ventas Totales' in df.columns and 'Tiempo' in df.columns and 'Reposición (días)' in df.columns:
            df['Demanda diaria'] = df['Ventas Totales'] / df['Tiempo']
            df['Stock mínimo'] = df['Demanda diaria'] * df['Reposición (días)']
            df['Stock seguridad'] = df['Stock mínimo'] * 0.05
            df['Stock máximo'] = df['Stock mínimo'] + df['Stock seguridad']

        if 'Nombre Producto' in df.columns:
            df['Nombre Producto'] = df['Nombre Producto'].str.strip().str.lower()
        else:
            df['Nombre Producto'] = "Producto Genérico"

        total_ventas = 0
        total_gastos = 0
        producto_mas_vendido = "N/A"
        producto_menos_vendido = "N/A"
        alerta_presupuesto = ""
        gastos_por_mes = pd.DataFrame(columns=['Mes', 'Gastos(compras)'])

        if 'Ventas' in df.columns and not df['Ventas'].empty:
            total_ventas = df['Ventas'].sum()
            df_ventas = df.groupby('Nombre Producto')['Ventas'].sum().reset_index()
            if not df_ventas.empty:
                producto_mas_vendido = df_ventas.loc[df_ventas['Ventas'].idxmax()]['Nombre Producto']
                producto_menos_vendido = df_ventas.loc[df_ventas['Ventas'].idxmin()]['Nombre Producto']
        
        if 'Fecha' in df.columns:
            df['Fecha'] = pd.to_datetime(df['Fecha'], dayfirst=False, errors='coerce')
            df['Mes'] = df['Fecha'].dt.strftime('%B %Y')
            
            if 'Ventas' in df.columns:
                df_ventas_mes = df.groupby(['Nombre Producto', 'Mes'])['Ventas'].sum().reset_index()
                df_ventas_mes.to_json("app/static/ventas_por_producto.json", orient='records')

            if 'Gastos(compras)' in df.columns:
                gastos_por_mes = df.groupby('Mes')['Gastos(compras)'].sum().reset_index()
                gastos_por_mes.to_json("app/static/gastos_por_mes.json", orient='records')

            if not gastos_por_mes.empty:
                total_gastos = gastos_por_mes['Gastos(compras)'].sum()
            
            saldo_final = presupuesto_mensual + total_ventas - total_gastos
            if saldo_final < 0:
                deficit = abs(saldo_final)
                alerta_presupuesto = f"¡Alerta! Tienes un déficit de {format_currency_string(deficit)}."
            
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

            if generar_graficos:
                
                if 'Stock mínimo' in df.columns and 'Stock máximo' in df.columns and 'Nombre Producto' in df.columns:
                    df_grafico = df_sorted.groupby('Nombre Producto').agg({
                        'Stock mínimo': 'mean',
                        'Stock máximo': 'mean'
                    }).reset_index()
                    
                    num_productos = len(df_grafico)
                    num_graficos_stock = (num_productos + 5) // 6
                    graficos_stock_nombres = []
                    for i in range(num_graficos_stock):
                        start_idx = i * 6
                        end_idx = start_idx + 6
                        df_chunk = df_grafico.iloc[start_idx:end_idx]
                        
                        plt.figure(figsize=(10, 6))
                        df_chunk.set_index('Nombre Producto').plot(kind='bar', stacked=True)
                        plt.title(f'Stock Mínimo y Máximo Promedio por Producto (Parte {i+1})')
                        plt.ylabel('Cantidad')
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        filename = f'app/static/grafico_stock_{i+1}.png'
                        plt.savefig(filename)
                        plt.close()
                        graficos_stock_nombres.append(filename.replace('app/static/', ''))
                    
                if 'Ventas' in df.columns and 'Nombre Producto' in df.columns:
                    df_grafico_ventas = df.groupby('Nombre Producto')['Ventas'].sum().reset_index()
                    
                    num_productos = len(df_grafico_ventas)
                    num_graficos_ventas = (num_productos + 5) // 6
                    graficos_ventas_nombres = []
                    for i in range(num_graficos_ventas):
                        start_idx = i * 6
                        end_idx = start_idx + 6
                        df_chunk = df_grafico_ventas.iloc[start_idx:end_idx]
                        
                        plt.figure(figsize=(10, 6))
                        plt.bar(df_chunk['Nombre Producto'], df_chunk['Ventas'], color='skyblue')
                        plt.title(f'Ventas Totales por Producto (Parte {i+1})')
                        plt.ylabel('Ventas')
                        plt.xlabel('Producto')
                        plt.xticks(rotation=45)
                        plt.tight_layout()
                        filename = f'app/static/grafico_ventas_{i+1}.png'
                        plt.savefig(filename)
                        plt.close()
                        graficos_ventas_nombres.append(filename.replace('app/static/', ''))
                
                with open("app/static/nombres_graficos.json", 'w') as f:
                    json.dump({"stock": graficos_stock_nombres, "ventas": graficos_ventas_nombres}, f)
            
            else:
                with open("app/static/nombres_graficos.json", 'w') as f:
                    json.dump({"stock": [], "ventas": []}, f)
        
        resumen_ventas = {
            'total_ventas': float(total_ventas),
            'producto_mas_vendido': producto_mas_vendido,
            'producto_menos_vendido': producto_menos_vendido,
            'alerta_presupuesto': alerta_presupuesto,
            'generar_graficos': generar_graficos,
            'presupuesto_mensual': presupuesto_mensual,
            'saldo_final': saldo_final
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
    try:
        with open("app/static/resumen_ventas.json", 'r') as f:
            resumen_ventas = json.load(f) if os.path.getsize("app/static/resumen_ventas.json") > 0 else {}
    except (FileNotFoundError, json.JSONDecodeError):
        resumen_ventas = {
            'total_ventas': 0,
            'producto_mas_vendido': 'N/A',
            'producto_menos_vendido': 'N/A',
            'alerta_presupuesto': '',
            'presupuesto_mensual': 0,
            'saldo_final': 0
        }
    
    try:
        with open("app/static/gastos_por_mes.json", 'r') as f:
            gastos_por_mes = json.load(f) if os.path.getsize("app/static/gastos_por_mes.json") > 0 else []
        total_gastos = sum(item.get('Gastos(compras)', 0) for item in gastos_por_mes)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        total_gastos = 0

    try:
        with open("app/static/ventas_por_producto.json", 'r') as f:
            ventas_por_producto = json.load(f) if os.path.getsize("app/static/ventas_por_producto.json") > 0 else []
        total_ventas = sum(item.get('Ventas', 0) for item in ventas_por_producto)
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        total_ventas = 0

    gasto_neto = total_gastos - total_ventas

    return render_template(
        "dashboard.html",
        resumen=resumen_ventas,
        total_gastos=total_gastos,
        total_ventas=total_ventas,
        gasto_neto=gasto_neto,
        saldo_final=resumen_ventas.get('saldo_final', 0)
    )

@main_bp.route("/descargar-plantilla")
def descargar_plantilla():
    return send_from_directory(
        os.path.join(os.getcwd(), 'app', 'static'),
        'Plantilla_Inventario_Usuario.xlsx',
        as_attachment=True
    )