from pathlib import Path
import json
import sys

# Construir ruta relativa (funciona en script y en notebooks)
try:
    base_dir = Path(__file__).parent
except NameError:
    base_dir = Path.cwd()  # si estás en REPL/notebook

ruta = base_dir / "Documentos" / "Dataset_entrevistas" / "news_dialogue.json"

if not ruta.exists():
    print(f"Archivo no encontrado: {ruta}")
    sys.exit(1)

def procesar_json_array(path):
    """Lee un archivo que contiene un array JSON grande y muestra las primeras n entradas sin cargar todo si es posible."""
    with path.open("r", encoding="utf-8") as f:
        texto = f.read().lstrip()
        if not texto:
            print("Archivo vacío")
            return
        if texto[0] != "[":
            print("No parece ser un array JSON. Intenta JSONL (1 JSON por línea).")
            return
        try:
            arr = json.loads(texto)
            data = []
            for i, registro in enumerate(arr):
                title = registro.get("title", "<sin title>")
                summary = registro.get("summary", "<sin descripción>")
                transcript = str(registro.get("utt", "<sin transcripcion>"))
                data.append([title, summary, transcript])
        except MemoryError:
            print("El archivo es demasiado grande para cargarlo entero en memoria.")
        except Exception as e:
            print("Error al parsear JSON array:", e)
        return data
        
def procesar_archivo(ruta):
    with ruta.open("r", encoding="utf-8") as f:
        start = f.read(1024).lstrip()
        if not start:
            print("Archivo vacío")
            sys.exit(1)
        return procesar_json_array(ruta)