
from typing import TypedDict


class StateSchema(TypedDict):
    pregunta: str
    pregunta_reformulada: str
    historial: list
    contexto: str
    stream: str