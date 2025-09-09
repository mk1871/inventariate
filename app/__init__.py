from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
import os
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

    if database_url and database_url.strip():
        # Convertir postgres:// a postgresql:// para SQLAlchemy con psycopg3
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print(f"✅ Usando PostgreSQL en Render: {database_url}")
    else:
        # SQLite para desarrollo local
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventariate.db'
        print("✅ Usando SQLite local")

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    from .routes import main_bp
    app.register_blueprint(main_bp)

    # No crear tablas automáticamente en producción - usar migraciones
    if not database_url:  # Solo en desarrollo
        with app.app_context():
            try:
                db.create_all()
                print("✅ Tablas creadas/verificadas en SQLite")
            except Exception as e:
                print(f"⚠️ Error al crear tablas: {e}")

    return app