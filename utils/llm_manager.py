import os
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

load_dotenv()

def get_llm(
        modelo_hf: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
        modelo_local: str = "qwen2.5:3b",
        force_local: bool = False,
        temperature: float = 0.1
):
    """
    Inicializa la interfaz de Chat de LangChain.
    
    Por defecto intenta conectar vía API Nube con Hugging Face usando el modelo state-of-the-art:
    'Qwen/Qwen2.5-Coder-7B-Instruct' (disponible en Hugging Face Serverless API, súper rápido).
    
    Si 'HF_TOKEN' no está presente o falla la conexión, realiza un Fallback automático a ChatOllama (Local).
    
    Parámetros:
      - modelo_hf: Repositorio en Hugging Face (default: 'Qwen/Qwen2.5-7B-Instruct')
      - modelo_local: Modelo en Ollama local (default: 'qwen2.5:3b')
      - force_local: Si es True, omite la nube y fuerza el uso del modelo local en Ollama.
      - temperature: Control de creatividad (default: 0.1 para evitar alucinaciones).
    """
    hf_token = os.environ.get('HF_TOKEN')

    if hf_token and not force_local:
        print(f"[LLM Manager] ☁️ Conectando a Hugging Face API (Nube): {modelo_hf}...")
        try:
            endpoint = HuggingFaceEndpoint(
                repo_id=modelo_hf,
                task="text-generation",
                max_new_tokens=2500,
                temperature=temperature,
                huggingfacehub_api_token=hf_token,
                timeout=60
            )

            llm_cloud = ChatHuggingFace(llm=endpoint)
            # Prueba de conectividad rápida
            llm_cloud.invoke("ping")
            print(f"[LLM Manager] ✅ Conectado exitosamente a Hugging Face API ({modelo_hf}).")
            return llm_cloud

        except Exception as e:
            print(f"⚠️ Falló la conexión a Hugging Face Cloud: {str(e)}")
            print("[LLM Manager] 🔄 Activando Fallback -> Cambiando a modelo LOCAL (ChatOllama)...")

    else:
        if force_local:
            print("[LLM Manager] 🖥️ Modo LOCAL forzado por parámetro.")
        else:
            print("[LLM Manager] ⚠️ No se encontró HF_TOKEN en .env. Iniciando en modo LOCAL (ChatOllama)...")

    # Fallback / Ejecución Offline Local con Ollama
    try:
        print(f"[LLM Manager] 🖥️ Conectando a Ollama Local ({modelo_local})...")
        llm_local = ChatOllama(model=modelo_local, temperature=temperature, num_predict=2048)
        print(f"[LLM Manager] ✅ Conectado exitosamente a modelo local Ollama ({modelo_local}).")
        return llm_local

    except Exception as e:
        print(f"❌ Error CRÍTICO: No se pudo conectar ni a la Nube ni a ChatOllama local. Detalles: {e}")
        return None

