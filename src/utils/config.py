from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings
import os

load_dotenv()

def config_llm():
    MODEL_CHAT = os.getenv("MODEL_CHAT")

    llm = ChatOllama(model=MODEL_CHAT, temperature=0)
    return llm


def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])