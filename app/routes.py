from flask import Blueprint, render_template, request, send_file, redirect, url_for, send_from_directory, flash, session
import pandas as pd
from .pdf import generar_pdf
import os
import json
from datetime import datetime
import matplotlib.pyplot as plt

plt.switch_backend('Agg')
from . import db, bcrypt
from .models import User, History
from flask_login import login_user, current_user, logout_user, login_required
import io
import uuid
from .s3_utils import upload_file_obj_to_s3, download_file_obj_from_s3, generate_presigned_url

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


@main_bp.route("/inventario")
def inventario():
    """Página de inventario - AÑADIDA ESTA FUNCIÓN FALTANTE"""
    return render_template("inventario.html")


@main_bp.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Tu cuenta ha sido creada exitosamente!', 'success')
        return redirect(url_for('main.login'))
    return render_template('register.html')


@main_bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@main_bp.route("/upload", methods=["GET"])
@login_required
def upload():
    processed = request.args.get('processed')
    cache_buster = datetime.now().strftime('%Y%m%d%H%M%S')
    return render_template("upload.html", processed=processed, cache_buster=cache_buster)


@main_bp.route("/procesar", methods=["POST"])
@login_required
def procesar():
    if 'archivo' not in request.files:
        return redirect(url_for('main.upload', error="No se seleccionó ningún archivo."))

    archivo = request.files['archivo']
    if archivo.filename == '':
        return redirect(url_for('main.upload', error="No se seleccionó ningún archivo."))

    try:
        # Generar un ID único para esta sesión de procesamiento
        session_id = str(uuid.uuid4())
        bucket_name = os.getenv('S3_BUCKET_NAME')

        # Leer el Excel directamente desde el archivo subido
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
                # Guardar en S3 en lugar de local
                ventas_json = df_ventas_mes.to_json(orient='records')
                file_obj = io.BytesIO(ventas_json.encode('utf-8'))
                upload_file_obj_to_s3(file_obj, bucket_name, f"{session_id}/ventas_por_producto.json",
                                      'application/json')

            if 'Gastos(compras)' in df.columns:
                gastos_por_mes = df.groupby('Mes')['Gastos(compras)'].sum().reset_index()
                # Guardar en S3
                gastos_json = gastos_por_mes.to_json(orient='records')
                file_obj = io.BytesIO(gastos_json.encode('utf-8'))
                upload_file_obj_to_s3(file_obj, bucket_name, f"{session_id}/gastos_por_mes.json", 'application/json')

            if not gastos_por_mes.empty:
                total_gastos = gastos_por_mes['Gastos(compras)'].sum()

            saldo_final = presupuesto_mensual + total_ventas - total_gastos
            if saldo_final < 0:
                deficit = abs(saldo_final)
                alerta_presupuesto = f"¡Alerta! Tienes un déficit de {format_currency_string(deficit)}."

            # Save historical data to the database
            if current_user.is_authenticated:
                month_year = datetime.now().strftime('%B %Y')
                current_month_history = History.query.filter_by(user_id=current_user.id,
                                                                month=datetime.now().strftime('%B'),
                                                                year=datetime.now().year).first()
                if current_month_history:
                    current_month_history.balance = saldo_final
                else:
                    new_history = History(
                        month=datetime.now().strftime('%B'),
                        year=datetime.now().year,
                        balance=saldo_final,
                        owner=current_user
                    )
                    db.session.add(new_history)
                db.session.commit()

            if 'Stock Final' in df.columns and 'Nombre Producto' in df.columns:
                df_sorted = df.sort_values('Fecha')
                resumen_productos = df_sorted.groupby(['Nombre Producto', 'Mes']).agg(
                    Stock_Final_Ultimo_Dia=('Stock Final', 'last'),
                    Stock_Minimo_Promedio=('Stock mínimo', 'mean'),
                    Stock_Maximo_Promedio=('Stock máximo', 'mean')
                ).reset_index()
                # Guardar en S3
                productos_json = resumen_productos.to_json(orient='records')
                file_obj = io.BytesIO(productos_json.encode('utf-8'))
                upload_file_obj_to_s3(file_obj, bucket_name, f"{session_id}/resumen_productos.json", 'application/json')
            else:
                resumen_productos = pd.DataFrame()

            resumen_ventas = {
                'total_ventas': float(total_ventas),
                'producto_mas_vendido': producto_mas_vendido,
                'producto_menos_vendido': producto_menos_vendido,
                'alerta_presupuesto': alerta_presupuesto,
                'generar_graficos': generar_graficos,
                'presupuesto_mensual': presupuesto_mensual,
                'saldo_final': saldo_final
            }
            # Guardar en S3
            resumen_json = json.dumps(resumen_ventas)
            file_obj = io.BytesIO(resumen_json.encode('utf-8'))
            upload_file_obj_to_s3(file_obj, bucket_name, f"{session_id}/resumen_ventas.json", 'application/json')

            if generar_graficos:
                # Inicializar listas para nombres de gráficos
                graficos_stock_nombres = []
                graficos_ventas_nombres = []

                if 'Stock mínimo' in df.columns and 'Stock máximo' in df.columns and 'Nombre Producto' in df.columns:
                    df_grafico = df_sorted.groupby('Nombre Producto').agg({
                        'Stock mínimo': 'mean',
                        'Stock máximo': 'mean'
                    }).reset_index()

                    num_productos = len(df_grafico)
                    num_graficos_stock = (num_productos + 5) // 6

                    for i in range(num_graficos_stock):
                        start_idx = i * 6
                        end_idx = start_idx + 6
                        df_chunk = df_grafico.iloc[start_idx:end_idx]

                        plt.figure(figsize=(10, 6))
                        df_chunk.set_index('Nombre Producto').plot(kind='bar', stacked=True)
                        plt.title(f'Stock Mínimo y Máximo Promedio por Producto (Parte {i + 1})')
                        plt.ylabel('Cantidad')
                        plt.xticks(rotation=45)
                        plt.tight_layout()

                        # Guardar gráfico en buffer y subir a S3
                        img_buffer = io.BytesIO()
                        plt.savefig(img_buffer, format='png')
                        img_buffer.seek(0)
                        upload_file_obj_to_s3(img_buffer, bucket_name, f"{session_id}/grafico_stock_{i + 1}.png",
                                              'image/png')
                        plt.close()

                        graficos_stock_nombres.append(f"grafico_stock_{i + 1}.png")

                if 'Ventas' in df.columns and 'Nombre Producto' in df.columns:
                    df_grafico_ventas = df.groupby('Nombre Producto')['Ventas'].sum().reset_index()

                    num_productos = len(df_grafico_ventas)
                    num_graficos_ventas = (num_productos + 5) // 6

                    for i in range(num_graficos_ventas):
                        start_idx = i * 6
                        end_idx = start_idx + 6
                        df_chunk = df_grafico_ventas.iloc[start_idx:end_idx]

                        plt.figure(figsize=(10, 6))
                        plt.bar(df_chunk['Nombre Producto'], df_chunk['Ventas'], color='skyblue')
                        plt.title(f'Ventas Totales por Producto (Parte {i + 1})')
                        plt.ylabel('Ventas')
                        plt.xlabel('Producto')
                        plt.xticks(rotation=45)
                        plt.tight_layout()

                        # Guardar gráfico en buffer y subir a S3
                        img_buffer = io.BytesIO()
                        plt.savefig(img_buffer, format='png')
                        img_buffer.seek(0)
                        upload_file_obj_to_s3(img_buffer, bucket_name, f"{session_id}/grafico_ventas_{i + 1}.png",
                                              'image/png')
                        plt.close()

                        graficos_ventas_nombres.append(f"grafico_ventas_{i + 1}.png")

                # Guardar nombres de gráficos en S3
                nombres_graficos = {"stock": graficos_stock_nombres, "ventas": graficos_ventas_nombres}
                nombres_json = json.dumps(nombres_graficos)
                file_obj = io.BytesIO(nombres_json.encode('utf-8'))
                upload_file_obj_to_s3(file_obj, bucket_name, f"{session_id}/nombres_graficos.json", 'application/json')
            else:
                # Guardar JSON vacío para gráficos
                nombres_graficos = {"stock": [], "ventas": []}
                nombres_json = json.dumps(nombres_graficos)
                file_obj = io.BytesIO(nombres_json.encode('utf-8'))
                upload_file_obj_to_s3(file_obj, bucket_name, f"{session_id}/nombres_graficos.json", 'application/json')

        # Guardar el Excel procesado en S3
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        upload_file_obj_to_s3(excel_buffer, bucket_name, f"{session_id}/inventario_calculado.xlsx",
                              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # Guardar session_id en la sesión de usuario para acceder luego
        session['processing_session'] = session_id
        session['bucket_name'] = bucket_name

        return redirect(url_for('main.upload', processed='True'))

    except Exception as e:
        return render_template("upload.html", error=f"Error al procesar el archivo: {e}"), 500


@main_bp.route("/history")
@login_required
def history():
    history_records = History.query.filter_by(owner=current_user).order_by(History.date_recorded.desc()).limit(12).all()
    return render_template('history.html', history_records=history_records)


@main_bp.route("/generar_pdf")
@login_required
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
@login_required
def dashboard():
    try:
        session_id = session.get('processing_session')
        bucket_name = session.get('bucket_name')

        if session_id and bucket_name:
            # Descargar resumen_ventas.json desde S3
            resumen_content = download_file_obj_from_s3(bucket_name, f"{session_id}/resumen_ventas.json")
            if resumen_content:
                resumen_ventas = json.loads(resumen_content.getvalue().decode('utf-8'))
            else:
                resumen_ventas = {
                    'total_ventas': 0,
                    'producto_mas_vendido': 'N/A',
                    'producto_menos_vendido': 'N/A',
                    'alerta_presupuesto': '',
                    'presupuesto_mensual': 0,
                    'saldo_final': 0
                }

            # Descargar gastos_por_mes.json desde S3
            gastos_content = download_file_obj_from_s3(bucket_name, f"{session_id}/gastos_por_mes.json")
            if gastos_content:
                gastos_por_mes = json.loads(gastos_content.getvalue().decode('utf-8'))
                total_gastos = sum(item.get('Gastos(compras)', 0) for item in gastos_por_mes)
            else:
                total_gastos = 0

            # Descargar ventas_por_producto.json desde S3
            ventas_content = download_file_obj_from_s3(bucket_name, f"{session_id}/ventas_por_producto.json")
            if ventas_content:
                ventas_por_producto = json.loads(ventas_content.getvalue().decode('utf-8'))
                total_ventas = sum(item.get('Ventas', 0) for item in ventas_por_producto)
            else:
                total_ventas = 0
        else:
            resumen_ventas = {
                'total_ventas': 0,
                'producto_mas_vendido': 'N/A',
                'producto_menos_vendido': 'N/A',
                'alerta_presupuesto': '',
                'presupuesto_mensual': 0,
                'saldo_final': 0
            }
            total_gastos = 0
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

    except Exception as e:
        flash(f"Error al cargar el dashboard: {str(e)}", "danger")
        return render_template(
            "dashboard.html",
            resumen={},
            total_gastos=0,
            total_ventas=0,
            gasto_neto=0,
            saldo_final=0
        )


@main_bp.route("/descargar-plantilla")
def descargar_plantilla():
    return send_from_directory(
        os.path.join(os.getcwd(), 'app', 'static'),
        'Plantilla_Inventario_Usuario.xlsx',
        as_attachment=True
    )