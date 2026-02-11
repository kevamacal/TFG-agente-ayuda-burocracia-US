import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_classic.chains.retrieval import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

embedding_model_name = os.getenv("MODEL") 
print(f"🔍 Cargando buscador con: {embedding_model_name}")
embeddings = OllamaEmbeddings(model=embedding_model_name)
chat_model_name = "llama3.2"
print(f"🧠 Cargando cerebro con: {chat_model_name}")
llm = ChatOllama(model=chat_model_name)

if not os.path.exists("./chroma.db"):
    print("❌ Error: No existe la carpeta 'chroma.db'. Ejecuta primero el script de ingestión.")
    exit()

vectorstore = Chroma(persist_directory="./chroma.db", embedding_function=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})    

system_prompt = (
    "Eres un asistente experto en analizar entrevistas. "
    "Usa los siguientes fragmentos de contexto recuperados para responder a la pregunta. "
    "Si no sabes la respuesta, di que no lo sabes. "
    "Mantén la respuesta concisa."
    "\n\n"
    "{context}"
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)

print("\n💬 ¡Chatbot iniciado! Pregunta sobre las entrevistas (escribe 'salir' para terminar).")

while True:
    query = input("\n👤 Tú: ")
    if query.lower() in ["salir", "exit", "chau"]:
        break
    
    print("🤖 Pensando...")
    try:
        response = rag_chain.invoke({"input": query})
        print(f"🤖 Bot: {response['answer']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
