import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import Chroma

def procersar_y_guardar_manuales():
    #Definir rutas de origen
    directorio_data = "./data/manuales"
    directorio_vectorial = "./chroma_db"

    if not os.path.exists(directorio_data):
        print(f"Error: la carpeta '{directorio_data}' no existe, favotr de crearla")
        return
    
    documentos_cargados = []

    # Cargar los pdf
    print("Buscando manuales tecnicos en la carpeta /data/manuales ...")
    for archivo in os.listdir(directorio_data):
        if archivo.endswith(".pdf"):
            ruta_completa = os.path.join(directorio_data, archivo)
            print(f"-> Cargando de forma secuencial: {archivo}")
            try:
                loader = PyPDFLoader(ruta_completa)
                documentos_cargados.extend(loader.load())
            except Exception as e:
                print(f"No se pudo cargar el archigo {archivo}. Error")

    if not documentos_cargados:
        print("No se econtraromn manuales pdf en la carpeta /data/manuales")

    print(f"\nTotal de paginas extraidas y cargadas en memoria: {len(documentos_cargados)}")


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