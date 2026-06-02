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
        logger.exception(f"Error realizando búsqueda en DuckDuckGo: {e}")
        return []

def procesar_resultados_busqueda(resultados: list, contexto_previo: str = "", referencias_previas: list = None) -> tuple[str, list]:
    """Procesa los resultados crudos de búsqueda de DuckDuckGo,
    los formatea como contexto web y los fusiona con el contexto y referencias previos."""
    if referencias_previas is None:
        referencias_previas = []
        
    contextos_web = []
    referencias_web = []
    
    for r in resultados:
        titulo = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href", "")
        
        # Validar y limpiar la URL
        if not href or not href.startswith("http"):
            continue
            
        # Limpiar parámetros de tracking si es una redirección de buscador
        if "?" in href and ("event=" in href or "url=" in href or "click" in href or "tracking" in href):
            import re
            dest_match = re.search(r'(?:[?&]url|[?&]q)=(https?://[^&]+)', href)
            if dest_match:
                import urllib.parse
                href = urllib.parse.unquote(dest_match.group(1))
            else:
                href = href.split("?")[0]
                
        contextos_web.append(f"FUENTE WEB (site:us.es): {titulo} ({href})\n{body}")
        referencias_web.append(f"{titulo} (Web US: {href})")
        
    contexto_web_final = "\n\n---\n\n".join(contextos_web)
    
    if contexto_previo and contexto_web_final:
        contexto_combinado = contexto_previo + "\n\n---\n\n" + contexto_web_final
    else:
        contexto_combinado = contexto_web_final or contexto_previo
        
    referencias_combinadas = list(set(referencias_previas + referencias_web))
    
    return contexto_combinado, referencias_combinadas
