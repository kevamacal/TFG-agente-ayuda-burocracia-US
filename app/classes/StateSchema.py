
from typing import TypedDict


class StateSchema(TypedDict):
    pregunta: str
    historial: list
    contexto: str
    stream: str