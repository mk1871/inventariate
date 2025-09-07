from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'tu_clave_secreta_aqui')  # <- Modificar esta línea
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///inventariate.db')  # <- Modificar esta línea
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    login_manager.login_view = 'main.login'
    login_manager.login_message_category = 'info'

    from .routes import main_bp
    app.register_blueprint(main_bp)

    with app.app_context():
        from . import models
        db.create_all()

    return app