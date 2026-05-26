from ddgs import DDGS
import logging

logger = logging.getLogger(__name__)

def limpiar_query_busqueda(query: str) -> str:
    """Limpia la query conversacional eliminando stop-words y palabras interrogativas para optimizar la búsqueda en DDG"""
    stopwords = {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "a", 
        "en", "y", "o", "u", "para", "por", "con", "como", "que", "es", "son", "se",
        "mi", "tu", "su", "mis", "tus", "sus", "sobre", "esta", "este", "estos", "estas",
        "donde", "dónde", "cómo", "como", "cuándo", "cuando", "cuál", "cual", "cuáles", "cuales",
        "qué", "que", "quién", "quien", "encuentra", "encuentran", "ubica", "ubican", "saber",
        "sabes", "dime", "busca", "buscar", "por-favor", "favor", "us", "universidad", "sevilla"
    }
    
    # Quitar signos y dividir
    limpia = query.replace("¿", "").replace("?", "").replace("¡", "").replace("!", "").replace(",", "").replace(".", "").replace(":", "")
    palabras = limpia.split()
    
    # Filtrar palabras de ruido
    filtradas = [w for w in palabras if w.lower() not in stopwords and len(w) > 2]
    
    if filtradas:
        return " ".join(filtradas)
    return " ".join(palabras)

def buscar_web_us(query: str, max_results: int = 4):
    """Realiza una búsqueda en DuckDuckGo restringida al dominio de la Universidad de Sevilla (site:us.es)"""
    try:
        query_limpia = limpiar_query_busqueda(query)
        search_query = f"{query_limpia} site:us.es"
        
        with DDGS() as ddgs:
            results = ddgs.text(search_query, max_results=max_results)
            return [
                {
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "href": r.get("href", "")
                }
                for r in results
            ]
    except Exception as e:
        logger.error(f"Error realizando búsqueda en DuckDuckGo: {e}")
        return []
