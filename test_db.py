import os
from app import create_app, db

app = create_app()

with app.app_context():
    try:
        result = db.engine.execute("SELECT version()")
        print("✅ Conexión exitosa a PostgreSQL:")
        print(result.fetchone())
    except Exception as e:
        print(f"❌ Error de conexión: {e}")