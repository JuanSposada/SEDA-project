import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

load_dotenv()

def get_llm(
        modelo_hf="Qwen/Qwen2.5-7B-Instruct",
        modelo_local="qwen2.5:3b",
):
    """
    Intenta inicializar un modelo de CHAT a través de la API de Hugging Face (Nube).
    Si falla (sin internet, timeout o error de servidor), hace fallback a ChatOllama (Local).
    Ambos devuelven una interfaz de Chat compatible con LangChain (.invoke, JSON, Tools).
    """
    hf_token = os.environ.get('HF_TOKEN')

    if hf_token:
        print(f"[Sistema] Intentando conectar a Hugging Face (Cloud Chat) con: {modelo_hf}...")
        try:
            # Se Crea el endpoint para interactuar con HuggingFace
            endpoint = HuggingFaceEndpoint(
                repo_id=modelo_hf,
                task="text-generation",
                max_new_tokens=1024,
                temperature=0.1,
                huggingfacehub_api_token=hf_token,
                timeout=30
            )

            llm_cloud = ChatHuggingFace(llm=endpoint)

            llm_cloud.invoke("test")
            return llm_cloud
        except Exception as e:
            print(f"Falló la conexión al modelo en la nube: {str(e)}")
            print("[Sistema] Iniciando Fallback -> Cambiando a modelo LOCAL (ChatOllama)...")

    else:
        print("No se encontró HF_TOKEN en el entorno. Iniciando en modo LOCAL (ChatOllama)...")

    # Fallback Offline
    try:
        llm_local = ChatOllama(model=modelo_local, temperature=0.1)
        print(f"onectado al modelo local: ChatOllama ({modelo_local})")
        return llm_local
    except Exception as e:
        print(f"Error CRÍTICO: No se pudo conectar ni a la nube ni a ChatOllama. Detalles: {e}")
        return None
