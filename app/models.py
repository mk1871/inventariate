from . import db, login_manager, bcrypt
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id: str):
    # para Flask-SQLAlchemy 3.x, mejor db.session.get
    return db.session.get(User, int(user_id))

class User(db.Model, UserMixin):
    __tablename__ = "users"  # <- antes implícito "user" pero tiene problemas con palabras reservadas
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, index=True, nullable=False)
    # 60 funciona para bcrypt (cost=12), pero dejamos margen
    password = db.Column(db.String(128), nullable=False)

    # relación a History; si quieres borrar histórico al borrar usuario, activa cascade
    history = db.relationship(
        "History",
        backref="owner",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"User('{self.username}')"

    def set_password(self, password: str):
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password, password)

class History(db.Model):
    __tablename__ = "history"
    id = db.Column(db.Integer, primary_key=True)
    month = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    balance = db.Column(db.Float, nullable=False)
    date_recorded = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # FK debe apuntar al nuevo nombre de tabla
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
