from dotenv import load_dotenv
from langchain_ollama import ChatOllama, OllamaEmbeddings
import os
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

load_dotenv()

def config_llm():
    HUGGINGFACEHUB_API_KEY = os.getenv("HUGGINGFACEHUB_API_KEY")
    HUGGINGFACEHUB_MODEL = os.getenv("HUGGINGFACEHUB_MODEL")

    endpoint = HuggingFaceEndpoint(repo_id=HUGGINGFACEHUB_MODEL, temperature=0.7, huggingfacehub_api_token=HUGGINGFACEHUB_API_KEY)
    llm = ChatHuggingFace(llm=endpoint)
    return llm


def format_docs(docs):
    return "\n\n".join([d.page_content for d in docs])