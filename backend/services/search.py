from duckduckgo_search import DDGS

def buscar_web_us(query: str, max_results: int = 4):
    """Realiza una búsqueda en DuckDuckGo restringida al dominio de la Universidad de Sevilla (site:us.es)"""
    try:
        print(f"🔍 [WEB SEARCH] Buscando en internet: '{query} site:us.es'")
        with DDGS() as ddgs:
            search_query = f"{query} site:us.es"
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
        print(f"Error realizando búsqueda en DuckDuckGo: {e}")
        return []
