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

    # ✅ Configuración de base de datos
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Convertir postgres:// a postgresql:// para SQLAlchemy
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        print("✅ Usando PostgreSQL en Render")
    else:
        # SQLite para desarrollo local
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventariate.db'
        print("✅ Usando SQLite local")

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tu_clave_secreta_aqui')

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)  # ✅ Inicializar Flask-Migrate

    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    from .routes import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        # Solo para desarrollo - no necesario con migraciones
        try:
            db.create_all()
            print("✅ Tablas creadas/verificadas")
        except Exception as e:
            print(f"⚠️ Error al crear tablas: {e}")

    return app