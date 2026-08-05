import os
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv

load_dotenv()

def procesar_y_guardar_manuales():
    #Definir rutas de origen
    directorio_data = "./data/manuales"
    directorio_vectorial = "./chroma_db"

    if not os.path.exists(directorio_data):
        print(f"Error: la carpeta '{directorio_data}' no existe, favotr de crearla")
        return
    
    documentos_cargados = []

    # Cargar los pdf
    print("Buscando manuales tecnicos recursivamente en la carpeta /data/manuales y subcarpetas...")

    loader = DirectoryLoader(
        directorio_data,
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=True
    )

    try:
        documentos_cargados = loader.load()
        print(f"Total de documentos cargados: {len(documentos_cargados)}")
    except Exception as e:
        print(f"Error al cargar los documentos: {e}")
        return

    if not documentos_cargados:
        print("No se encontraron documentos PDF en la carpeta especificada.")
        return

    # Text splitter, para semegmetacion semantica, ajustamos los chunks con 700 caracteres
    # y un overlap de 120
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=120)
    print("Segmentando texto en fragmentos optimizados para el modelo...")
    fragmentos_texto = text_splitter.split_documents(documentos_cargados)
    print(f"Total de fragmentos generados: {len(fragmentos_texto)}")

    # Embeddings y Vector Store para persistencia local
    print("\nInicializando el modelo de embeddings local(all-MiniLM-L6-v2)...")
    # Modelo que corre 100& local y consume pocos recutsos
    modelo_embeddings = HuggingFaceBgeEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    print("Construyendo base de datos vectorial en ChromaDB y guardanfdo en disco...")
    vector_store = Chroma.from_documents(
        documents=fragmentos_texto,
        embedding=modelo_embeddings,
        persist_directory=directorio_vectorial
    )

    print(f"!Proceso completado con exito! Base de conocimiento persistida en: {directorio_vectorial}")

if __name__ == "__main__":
    procersar_y_guardar_manuales()