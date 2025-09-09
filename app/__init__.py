import re
import os
import secrets
import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from dotenv import load_dotenv

# Cargar variables de entorno SOLO si hay .env presente (dev local)
if os.path.exists(".env"):
    load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()

def _mask_conn_str(url: str) -> str:
    """Enmascara usuario y password en la URL para logs seguros."""
    # p.ej: postgresql+psycopg://user:pass@host:5432/db -> postgresql+psycopg://***:***@host/db
    try:
        import urllib.parse as up
        parsed = up.urlsplit(url)
        netloc = parsed.netloc
        if "@" in netloc:
            creds, host = netloc.split("@", 1)
            if ":" in creds:
                user, _pwd = creds.split(":", 1)
                masked_creds = f"{user}:***"
            else:
                masked_creds = "***"
            netloc_masked = f"{masked_creds}@{host}"
        else:
            netloc_masked = netloc
        path = parsed.path.rsplit("/", 1)[-1] if parsed.path else ""
        return f"{parsed.scheme}://{netloc_masked}/{path}".rstrip("/")
    except Exception:
        return "****"

def create_app():
    app = Flask(__name__)

    # ===== SECRET_KEY seguro =====
    secret = os.getenv("SECRET_KEY")
    if secret:
        app.config["SECRET_KEY"] = secret
    else:
        # En Render (producción) exigimos SECRET_KEY; en local generamos uno efímero
        is_render = os.getenv("RENDER") or os.getenv("RENDER_INTERNAL_HOSTNAME") or os.getenv("RENDER_EXTERNAL_URL")
        if is_render:
            raise RuntimeError("SECRET_KEY no está configurado en el entorno (Render). Añádelo como env var/secret.")
        app.config["SECRET_KEY"] = "dev-" + secrets.token_hex(32)

    # ===== Base de datos =====
    raw_url = os.getenv("DATABASE_URL")
    masked = _mask_conn_str(raw_url) if raw_url else "sqlite:///inventariate.db"
    print(f"🔍 DATABASE_URL (mascada): {masked}")

    if raw_url:
        # Convierte postgres:// o postgresql:// → postgresql+psycopg:// (psycopg3)
        url = re.sub(r"^postgres(ql)?:\/\/", "postgresql+psycopg://", raw_url)
        app.config["SQLALCHEMY_DATABASE_URI"] = url
        print(f"✅ Driver psycopg3 activado → { _mask_conn_str(url) }")
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///inventariate.db"
        print("✅ Usando SQLite local")

    # Opcional: mejora de rendimiento/logs
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "main.login"
    login_manager.login_message_category = "info"

    from .routes import main_bp
    app.register_blueprint(main_bp)

    # Log de driver y prueba de conexión (no imprime secretos)
    try:
        engine = sa.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        app.logger.info(f"SQLAlchemy {sa.__version__}, driver: {engine.dialect.driver}")
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
            app.logger.info("Conexión a DB verificada (SELECT 1 OK).")
    except Exception as e:
        app.logger.error(f"Engine creation/connection failed: {e}")

    # No crear tablas automáticamente en producción - usar migraciones
    if not raw_url:  # Solo en desarrollo local con SQLite
        with app.app_context():
            try:
                db.create_all()
                print("✅ Tablas creadas/verificadas en SQLite")
            except Exception as e:
                print(f"⚠️ Error al crear tablas: {e}")

    return app
