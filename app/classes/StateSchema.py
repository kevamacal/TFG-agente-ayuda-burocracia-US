
from typing import TypedDict


class StateSchema(TypedDict):
    pregunta: str
    pregunta_reformulada: str
    historial: list
    historial_formateado:list
    contexto: str
    stream: str
    referencias: list