import re
import os
import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # ✅ Configuración de base de datos para Render
    database_url = os.getenv('DATABASE_URL')

    print(f"🔍 DATABASE_URL desde entorno: {database_url}")

    if database_url:
        # Convierte postgres:// o postgresql:// → postgresql+psycopg://
        database_url = re.sub(r'^postgres(ql)?:\/\/', 'postgresql+psycopg://', database_url)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print(f"✅ Usando PostgreSQL con psycopg3: {database_url}")
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventariate.db'
        print("✅ Usando SQLite local")

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    from .routes import main_bp
    app.register_blueprint(main_bp)

    # 🔎 (1) LOG INMEDIATO AL ARRANCAR: crea un engine temporal y loguea driver
    try:
        engine = sa.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        app.logger.info(f"SQLAlchemy {sa.__version__}, driver: {engine.dialect.driver}")
        # Opcional: forzar una conexión para validar credenciales/driver
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
            app.logger.info("Conexión a DB verificada (SELECT 1 OK).")
    except Exception as e:
        app.logger.error(f"Engine creation/connection failed: {e}")

    # 🕐 (2) LOG EN LA PRIMERA PETICIÓN HTTP
    @app.before_first_request
    def log_sqlalchemy_info():
        try:
            engine = sa.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
            app.logger.info(f"[on first request] SQLAlchemy {sa.__version__}, driver: {engine.dialect.driver}")
        except Exception as e:
            app.logger.error(f"[on first request] Engine creation failed: {e}")

    # No crear tablas automáticamente en producción - usar migraciones
    if not database_url:  # Solo en desarrollo local con SQLite
        with app.app_context():
            try:
                db.create_all()
                print("✅ Tablas creadas/verificadas en SQLite")
            except Exception as e:
                print(f"⚠️ Error al crear tablas: {e}")

    return app