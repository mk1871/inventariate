# test_db.py - versión mejorada
import os
from app import create_app, db

app = create_app()

with app.app_context():
    try:
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"🔍 URL de base de datos: {database_url}")

        if 'postgres' in database_url:
            # Test para PostgreSQL
            with db.engine.connect() as connection:
                result = connection.execute(db.text("SELECT version()"))
                print("✅ Conexión exitosa a PostgreSQL:")
                print(result.fetchone())
        else:
            # Test para SQLite
            with db.engine.connect() as connection:
                result = connection.execute(db.text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = result.fetchall()
                print("✅ Conexión exitosa a SQLite")
                print(f"📊 Tablas encontradas: {len(tables)}")
                for table in tables[:5]:  # Muestra las primeras 5 tablas
                    print(f"  - {table[0]}")

    except Exception as e:
        print(f"❌ Error de conexión: {e}")