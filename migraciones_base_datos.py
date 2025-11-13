# migraciones_base_datos.py
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_batch
import sys, os
from dotenv import load_dotenv
from parse_dataset import procesar_archivo

load_dotenv()
# === CONFIGURACIÓN DE CONEXIÓN ===
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),  
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}

# === RUTA AL DATASET ===
try:
    base_dir = Path(__file__).parent
except NameError:
    base_dir = Path.cwd()

RUTA_DATASET = base_dir / "Documentos" / "Dataset_entrevistas" / "news_dialogue.json"

# === FUNCIONES ===
def iniciar_conexion():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print("❌ Error al conectar a la base de datos:", e)
        sys.exit(1)

def crear_tabla():
    conn = iniciar_conexion()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entrevistas (
            id SERIAL PRIMARY KEY,
            titulo TEXT,
            resumen TEXT,
            transcripcion TEXT
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Tabla 'entrevistas' verificada o creada.")

def migrar_base_datos(path, chunk_size=1000):
    crear_tabla()
    conn = iniciar_conexion()
    cur = conn.cursor()

    print("🚀 Iniciando migración a PostgreSQL...")
    batch = []
    total = 0

    for registro in procesar_archivo(path):
        batch.append(registro)
        if len(batch) >= chunk_size:
            execute_batch(cur, """
                INSERT INTO entrevistas (titulo, resumen, transcripcion)
                VALUES (%s, %s, %s)
            """, batch)
            conn.commit()
            total += len(batch)
            print(f"📦 Insertados {total:,} registros...")
            batch.clear()

    # Insertar el último bloque
    if batch:
        execute_batch(cur, """
            INSERT INTO entrevistas (titulo, resumen, transcripcion)
            VALUES (%s, %s, %s)
        """, batch)
        conn.commit()
        total += len(batch)

    cur.close()
    conn.close()
    print(f"🎉 Migración completada. Total registros: {total:,}")

# === PUNTO DE ENTRADA ===
if __name__ == "__main__":
    if not RUTA_DATASET.exists():
        print(f"❌ Archivo no encontrado: {RUTA_DATASET}")
        sys.exit(1)
    migrar_base_datos(RUTA_DATASET)
