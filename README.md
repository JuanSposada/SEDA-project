# 🚗 SEDA - Sistema Experto de Diagnóstico Automotriz e Inteligencia de Refacciones

**SEDA** es un prototipo de Sistema Experto e Inteligencia Artificial diseñado para la asistencia técnica automotriz, el diagnóstico de códigos de falla OBD-II (DTC), la recuperación semántica de manuales de servicio (RAG) y la identificación inteligente de refacciones compatibles.

Desarrollado como proyecto de **Residencias Profesionales**.

---

## 📌 Características Principales

- 🔍 **Consulta de Códigos OBD-II (DTC)**: Base de datos relacional SQLite indexada (`dtc_codes.db`) con miles de códigos estándar y específicos por fabricante (Acura, Honda, Toyota, Nissan, etc.).
- 🧠 **Motor NLP con spaCy**: Extracción automatizada de componentes técnicos a partir de las descripciones de fallas mediante análisis morfosintáctico.
- 📚 **Arquitectura RAG (Retrieval-Augmented Generation)**: Ingesta de manuales técnicos en PDF, segmentación en *chunks* y almacenamiento en base de datos vectorial **ChromaDB** utilizando embeddings locales (`all-MiniLM-L6-v2`).
- 🤖 **Agente Autónomo con LangChain y Ollama**: Integración de modelos locales (`qwen2.5:3b`) equipados con herramientas (*tool binding*) para consultar la base de datos relacional y APIs externas.
- 🛒 **Búsqueda de Refacciones en Tiempo Real**: Conexión asíncrona con **RockAuto API** para localizar partes, números de parte y enlaces al catálogo.
- 🌐 **Inferencia Híbrida & Hugging Face**: Integración alternativa con `Qwen/Qwen2.5-Coder-7B-Instruct` vía la API de Hugging Face e interfaz gráfica interactiva construida en **Streamlit**.

---

## 🛠️ Arquitectura del Sistema

```
SEDA/
├── app.py                      # Interfaz gráfica interactiva Streamlit (Formulario + Chat Guiado)
├── agente_seda.py              # Agente de consola interactivo determinista
├── orchestator.py              # Orquestador del sistema experto y prompt maestro
├── identifying_engine.py       # Motor NLP con spaCy para extracción de componentes
├── ingesta_manuales.py         # Pipeline RAG: PyPDFLoader + TextSplitter + ChromaDB
├── inicializar_db.py           # Script de optimización e indexación de SQLite
├── utils/
│   ├── seda_engine.py          # Motor central del pipeline de diagnóstico y Q&A
│   ├── tools_seda.py           # Herramientas (DTC DB, FTS5, RAG ChromaDB, RockAuto, VIN)
│   ├── llm_manager.py          # Gestor de conexión híbrida (Hugging Face / Ollama)
│   └── make_manager.py         # Normalización de marcas padre y submarcas
├── scripts/
│   ├── generar_dataset_sft.py  # Generador de dataset de Fine-Tuning desde SQLite (7,081 ejemplos)
│   └── entrenar_finetuning_unsloth.py # Script de entrenamiento con QLoRA 4-bit (Unsloth)
├── data/
│   ├── dataset_seda_sft.jsonl  # Dataset generado para Fine-Tuning (ChatML)
│   ├── base_conocimiento.json  # Mapeo de síntomas, causas raíz y refacciones
│   ├── dtc_codes.db            # Base de datos SQLite SAE de códigos OBD-II
│   ├── seda_diagnostico.db     # Base de datos SQLite enriquecida con motor FTS5
│   └── manuales/               # Directorio para PDFs de manuales técnicos de taller
└── chroma_db/                  # Vectorstore persistente de ChromaDB (all-MiniLM-L6-v2)
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

### 2. Ejecutar Agente de Diagnóstico (Consola / CLI)

```bash
python agente_seda.py
```

### 3. Ejecutar Interfaz Web Interactiva (Streamlit)

```bash
streamlit run app.py
```

---

## 🔮 Trabajo a Futuro y Mejoras Propuestas (Roadmap)

Como parte de la evolución continua del proyecto de tesis / investigación, se contemplan las siguientes líneas de mejora:

1. **🎯 Fine-Tuning de Dominio Automotriz (SFT / QLoRA)**:
   - Entrenar un modelo con pesos propios (*SEDA-LLM*) a partir del dataset de **7,081 pares de entrenamiento** generado en `data/dataset_seda_sft.jsonl`.
   - Ejecutar el pipeline de afinamiento en hardware con GPU dedicada (NVIDIA RTX / Cloud GPU A100/T4) mediante el script preparado en `scripts/entrenar_finetuning_unsloth.py`.
   - Cuantizar el modelo a formato **GGUF** para permitir su ejecución 100% offline y ligera en **Ollama**.

2. **🔌 Conexión Directa con Escáneres OBD-II (ELM327 Bluetooth / Wi-Fi)**:
   - Lectura automatizada de códigos DTC y parámetros en vivo (*Live Data PIDs*: RPM, sensor MAF, temperatura de refrigerante, compensación de combustible STFT/LTFT) directamente desde el puerto OBD-II del automóvil.

3. **🖼️ Procesamiento Multimodal y OCR de Diagramas Eléctricos**:
   - Integración de modelos de visión para interpretar esquemas de cableado, diagramas de fusibles y pinouts a partir de imágenes y PDFs escaneados.

4. **🌐 Despliegue en la Nube y Dockerización**:
   - Creación de imágenes Docker optimizadas para despliegue en servidores cloud o plataformas locales de taller mecánico.

---

## 🔬 Tecnologías Empleadas

- **Lenguaje**: Python 3
- **Frameworks de IA / LLM**: LangChain, Ollama (`qwen2.5:3b`), Hugging Face Serverless API (`Qwen/Qwen2.5-Coder-7B-Instruct`)
- **Procesamiento de Lenguaje Natural (NLP)**: spaCy (`en_core_web_sm`)
- **Vector Database & Embeddings**: ChromaDB, `sentence-transformers/all-MiniLM-L6-v2`
- **Bases de Datos Relacionales**: SQLite 3 con índices FTS5
- **Frontend / UI**: Streamlit (Modo Formulario Directo y Modo Chat Asistente Guiado)
- **Integraciones**: RockAuto API & DuckDuckGo Search API

---

## 📝 Licencia & Créditos

Desarrollado como parte del proyecto de **Residencias Profesionales**.
Creditos al repositorio de https://github.com/Wal33D/dtc-database de donde tomamos la base de datos de codigos DTC.
Creditos al repositorio de https://github.com/rsp2k/rockauto-api la cual usamos para la utilidad de bisqueda de refacciones.