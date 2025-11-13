from pathlib import Path
import sys, sqlite3, psycopg2
from parse_dataset import procesar_archivo

try:
    base_dir = Path(__file__).parent
except NameError:
    base_dir = Path.cwd() 

RUTA_DATASET_ENTREVISTAS = base_dir / "Documentos" / "Dataset_entrevistas" / "news_dialogue.json"

if not RUTA_DATASET_ENTREVISTAS.exists():
    print(f"Archivo no encontrado: {RUTA_DATASET_ENTREVISTAS}")
    sys.exit(1)
    
def iniciar_conexion():
    conn = psycopg2.connect(
        dbname = "entrevistas-db",
        user = "kevamacal",
        password = "1234",
        host = "localhost",
        port = "5432"
    )
    return conn
    
def crear_base_datos():
    conn = iniciar_conexion()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS entrevistas(
            id SERIAL PRIMARY KEY,
            titulo TEXT,
            resumen TEXT,
            transcripcion TEXT
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()
    
def migrar_base_datos(data):
    crear_base_datos()
    conn = iniciar_conexion()
    cur = conn.cursor()
    cur.executemany('''
        INSERT INTO entrevistas (titulo, resumen, transcripcion)
        VALUES (%s, %s, %s)
    ''', data)
    conn.commit()
    cur.close()
    conn.close()
    
data = procesar_archivo(RUTA_DATASET_ENTREVISTAS)
migrar_base_datos(data)