import os
from flask import Flask
from dotenv import load_dotenv


load_dotenv()


def create_app():
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-key")


from .routes import main_bp
app.register_blueprint(main_bp)


return app