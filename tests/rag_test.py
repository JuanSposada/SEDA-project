from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# Inicializar mismo modelo de embeddings
modelo_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Cargar la base vectorial que acabamos de crear
vector_store = Chroma(persist_directory="./chroma_db", embedding_function=modelo_embeddings)

# Hacer una consulta técnica de prueba sobre tus manuales
query = """Throughout any vehicle, gaskets are used to seal the mating sur
faces between two parts and keep lubricants, fluids, vacuum or 
pressure contained in an assembly. """
print(f"Buscando en manuales locales: '{query}'...\n")

resultados = vector_store.similarity_search(query, k=2)

for i, doc in enumerate(resultados):
    print(f"--- Fragmento Encontrado {i+1} ---")
    print(f"Fuente: {doc.metadata.get('source')}")
    print(f"Contenido:\n{doc.page_content}\n")