# 🚗 SEDA - Sistema Experto de Diagnóstico Automotriz e Inteligencia de Refacciones

**SEDA** es un prototipo de Sistema Experto e Inteligencia Artificial diseñado para la asistencia técnica automotriz, el diagnóstico de códigos de falla OBD-II (DTC), la recuperación semántica de manuales de servicio (RAG) y la identificación inteligente de refacciones compatibles.

Desarrollado como proyecto de **Residencias Profesionales / Tesis de Ingeniería**.

---

## 📌 Características Principales

- 🔍 **Consulta de Códigos OBD-II (DTC)**: Base de datos relacional SQLite indexada (`dtc_codes.db`) con miles de códigos estándar y específicos por fabricante (Acura, Honda, Toyota, Nissan, etc.).
- 🧠 **Motor NLP con spaCy**: Extracción automatizada de componentes técnicos a partir de las descripciones de fallas mediante análisis morfosintáctico.
- 📚 **Arquitectura RAG (Retrieval-Augmented Generation)**: Ingesta de manuales técnicos en PDF, segmentación en *chunks* y almacenamiento en base de datos vectorial **ChromaDB** utilizando embeddings locales (`all-MiniLM-L6-v2`).
- 🤖 **Agente Autónomo con LangChain y Ollama**: Integración de modelos locales (`qwen2.5:3b`) equipados con herramientas (*tool binding*) para consultar la base de datos relacional y APIs externas.
- 🛒 **Búsqueda de Refacciones en Tiempo Real**: Conexión asíncrona con **RockAuto API** para localizar partes, números de parte y enlaces al catálogo.
- 🌐 **Inferencia Híbrida & Hugging Face**: Integración alternativa con `Meta-Llama-3-8B-Instruct` vía la API de Hugging Face e interfaz gráfica interactiva construida en **Streamlit**.

---

## 🛠️ Arquitectura del Sistema

```
SEDA/
├── agente_seda.py          # Agente principal LangChain con Ollama y Tool Binding
├── herramientas_seda.py    # Definición de herramientas (DTC DB y RockAuto API)
├── orchestator.py          # Orquestador del sistema experto y prompt maestro
├── identifying_engine.py   # Motor NLP con spaCy para parsing de descripciones
├── ingesta_manuales.py     # Pipeline RAG: PyPDFLoader + TextSplitter + Embeddings + ChromaDB
├── inicializar_db.py       # Script de optimización e indexación de SQLite
├── hugging_api.py          # Cliente de inferencia Hugging Face (Llama-3-8B)
├── hugging_app.py          # Interfaz web de usuario construida con Streamlit
├── data/
│   ├── base_conocimiento.json # Mapeo de síntomas, causas raíz y refacciones
│   ├── dtc_codes.db           # Base de datos SQLite con códigos OBD-II
│   └── manuales/              # Directorio para PDFs de manuales técnicos
├── chroma_db/              # Vectorstore persistente de ChromaDB
└── scrapping/              # Módulos de web scraping para refacciones
```

---

## 🚀 Requisitos e Instalación

### 1. Requisitos Previos

- **Python 3.10+**
- **Ollama** (Opcional si se utiliza el modelo local `qwen2.5:3b`):
  ```bash
  ollama pull qwen2.5:3b
  ```
- **Modelo de lenguaje spaCy para inglés**:
  ```bash
  python -m spacy download en_core_web_sm
  ```

### 2. Instalación de Dependencias

Clona o navega al directorio del proyecto y activa tu entorno virtual:

```bash
cd ~/residencias/SEDA
source venv/bin/activate
pip install -r requirements.txt
```

*Librerías principales empleadas*: `langchain`, `langchain-community`, `langchain-ollama`, `spacy`, `chromadb`, `sentence-transformers`, `streamlit`, `huggingface_hub`, `rockauto-api`.

---

## ⚙️ Uso del Sistema

### 1. Inicialización e Ingesta de Datos

- **Optimizar e Indexar Base de Datos DTC**:
  ```bash
  python inicializar_db.py
  ```

- **Ingestar Manuales Técnicos (RAG)**:
  Coloca los manuales en PDF en la carpeta `data/manuales/` y ejecuta:
  ```bash
  python ingesta_manuales.py
  ```

### 2. Ejecutar Agente de Diagnóstico (Consola / Ollama)

```bash
python agente_seda.py
```

### 3. Ejecutar Interfaz Web (Streamlit)

```bash
streamlit run hugging_app.py
```

---

## 🔬 Tecnologías Empleadas

- **Lenguaje**: Python 3
- **Frameworks de IA / LLM**: LangChain, Ollama (`qwen2.5:3b`), Hugging Face Inference API (`Meta-Llama-3-8B-Instruct`)
- **Procesamiento de Lenguaje Natural (NLP)**: spaCy (`en_core_web_sm`)
- **Vector Database & Embeddings**: ChromaDB, `sentence-transformers/all-MiniLM-L6-v2`
- **Base de Datos Relacional**: SQLite 3
- **Frontend / UI**: Streamlit
- **Integraciones**: RockAuto API

---

## 📝 Licencia & Créditos

Desarrollado como parte del proyecto de **Residencias Profesionales / Tesis de Ingeniería en Sistemas Automotrices e Inteligencia Artificial**.
