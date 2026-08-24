import streamlit as st
import json
import time
import re
from utils.seda_engine import execute_diagnostic_pipeline, answer_followup_question
from utils.tools_seda import tool_decodificar_vin
from utils.llm_manager import get_llm

# ==============================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==============================================================================
st.set_page_config(
    page_title="SEDA - Diagnóstico Automotriz Experto",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para interfaz moderna e ingeniería automotriz
st.markdown("""
<style>
    .status-ok {
        color: #10B981;
        font-weight: bold;
    }
    .status-alert {
        color: #EF4444;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# CACHÉ DE MODELOS
# ==============================================================================
@st.cache_resource(show_spinner=False)
def get_cached_llm(force_local: bool, temperature: float):
    return get_llm(force_local=force_local, temperature=temperature)

def format_web_results(raw_text: str) -> str:
    """Parsea y formatea resultados de búsqueda web (DuckDuckGo) a Markdown con viñetas y enlaces."""
    if not raw_text or not isinstance(raw_text, str):
        return "Sin resultados web."
    
    # Si ya viene formateado con markdown estructurado
    if "### 🌐" in raw_text or "1. 🛒" in raw_text:
        return raw_text

    # Si viene en formato raw de langchain (snippet: ..., title: ..., link: ...)
    pattern = r'snippet:\s*(.*?),\s*title:\s*(.*?),\s*link:\s*(https?://[^\s,\]]+)'
    matches = re.findall(pattern, raw_text, re.DOTALL)

    if matches:
        salida = "### 🌐 Refacciones y Tiendas Encontradas en la Web:\n\n"
        for i, (snippet, title, link) in enumerate(matches, 1):
            t_clean = title.strip()
            s_clean = snippet.strip().replace("\n", " ")
            l_clean = link.strip()
            salida += (
                f"{i}. 🛒 **[{t_clean}]({l_clean})**\n"
                f"   - 📝 **Detalle:** {s_clean}\n"
                f"   - 🔗 **Enlace Directo:** [{l_clean}]({l_clean})\n\n"
            )
        return salida.strip()

    return raw_text

# ==============================================================================
# INICIALIZACIÓN DE ESTADO (SESSION STATE)
# ==============================================================================
if "form_data" not in st.session_state:
    st.session_state.form_data = {
        "vin": "",
        "year": "",
        "make": "",
        "model": "",
        "tipo_falla": "DTC",
        "dtc_code": "",
        "sintomas": "",
        "vin_details": "No disponible"
    }

if "form_diagnosis_result" not in st.session_state:
    st.session_state.form_diagnosis_result = None

if "vin_decoded_data" not in st.session_state:
    st.session_state.vin_decoded_data = None

# Variables para el Modo Chat Guiado
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "chat_step" not in st.session_state:
    st.session_state.chat_step = "init"

if "chat_vehicle_data" not in st.session_state:
    st.session_state.chat_vehicle_data = {
        "year": "",
        "make": "",
        "model": "",
        "dtc_code": "",
        "sintomas": "",
        "vin_details": "No disponible"
    }

if "chat_diagnostic_result" not in st.session_state:
    st.session_state.chat_diagnostic_result = None

# ==============================================================================
# PANEL LATERAL (SIDEBAR) - CONFIGURACIÓN Y ESTADO
# ==============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/car.png", width=65)
    st.title("SEDA")
    st.caption("Sistema Experto de Diagnóstico Automotriz e Inteligencia de Refacciones")
    
    st.divider()
    
    st.subheader("⚙️ Motor de IA")
    provider = st.selectbox(
        "Proveedor LLM:",
        ["Hugging Face Cloud (Qwen2.5-Coder-7B)", "Ollama Local (qwen2.5:3b)"],
        index=0
    )
    
    force_local = "Ollama" in provider
    temp = st.slider("Temperatura (Creatividad):", min_value=0.0, max_value=0.6, value=0.1, step=0.05,
                     help="Valores bajos (0.0 - 0.1) evitan alucinaciones y garantizan apego estricto a los manuales de servicio.")

    # Instanciamos o recuperamos de caché
    active_llm = get_cached_llm(force_local, temp)

    if active_llm:
        st.markdown("<p class='status-ok'>● Motor de Inferencia Conectado</p>", unsafe_allow_html=True)
    else:
        st.markdown("<p class='status-alert'>● Error de Conexión LLM</p>", unsafe_allow_html=True)

    st.divider()

    st.subheader("📚 Arquitectura Multi-Fuente")
    st.markdown("""
    - 🔍 **Base SAE OBD-II**: `dtc_codes.db` (SQLite)
    - 🧠 **Contexto Experto**: `seda_diagnostico.db` (FTS5)
    - 📖 **Manuales de Taller (RAG)**: `ChromaDB`
    - 🛒 **Refacciones**: DuckDuckGo & RockAuto API
    """)

    st.divider()
    st.caption("Tesis de Ingeniería en Sistemas & Asistencia Automotriz")

st.title("🚗 SEDA: Asistente Experto en Diagnóstico Automotriz")
st.caption("Diagnóstico inteligente de fallas OBD-II, análisis de síntomas, extracción de manuales PDF y cotización de refacciones.")

tab_form, tab_chat = st.tabs(["📋 Modo Formulario (Diagnóstico Directo)", "💬 Modo Chat Guiado (Paso a Paso)"])

# ==============================================================================
# MODO 1: FORMULARIO ESTRUCTURADO (DIAGNÓSTICO DIRECTO)
# ==============================================================================
with tab_form:
    st.markdown("### 📝 Formulario de Entrada Técnica")

    # Función para cargar presets
    def load_preset(yr, mk, md, dtc, sint, vin=""):
        st.session_state.form_data["year"] = yr
        st.session_state.form_data["make"] = mk
        st.session_state.form_data["model"] = md
        st.session_state.form_data["dtc_code"] = dtc
        st.session_state.form_data["sintomas"] = sint
        st.session_state.form_data["vin"] = vin
        st.session_state.form_data["tipo_falla"] = "DTC" if dtc else "Síntomas"

    # Barra de Presets Rápidos
    with st.expander("⚡ Cargar Casos de Prueba Preconfigurados"):
        c_p1, c_p2, c_p3, c_p4 = st.columns(4)
        if c_p1.button("📌 Acura TL (P1106)"):
            load_preset("2000", "Acura", "TL", "P1106", "")
            st.rerun()
        if c_p2.button("📌 Honda Civic (P0300)"):
            load_preset("2018", "Honda", "Civic", "P0300", "")
            st.rerun()
        if c_p3.button("📌 Nissan Versa (Síntomas)"):
            load_preset("2015", "Nissan", "Versa", "", "Tiembla mucho en los semáforos, pierde potencia y tira humo negro por el escape.")
            st.rerun()
        if c_p4.button("📌 Toyota Corolla (P0171)"):
            load_preset("2016", "Toyota", "Corolla", "P0171", "")
            st.rerun()

    col_veh_1, col_veh_2 = st.columns([1, 1], gap="large")

    with col_veh_1:
        st.markdown("#### 1. Identificación del Vehículo")
        
        # Opción VIN
        vin_col1, vin_col2 = st.columns([3, 1])
        with vin_col1:
            vin_input = st.text_input(
                "Número VIN (Opcional - 17 Caracteres):",
                value=st.session_state.form_data.get("vin", ""),
                placeholder="Ej. 1HGCM82633A123456",
                max_chars=17
            ).strip().upper()
        with vin_col2:
            st.write("")
            st.write("")
            btn_decode = st.button("🔍 Decodificar", use_container_width=True)

        if btn_decode and vin_input:
            if len(vin_input) == 17:
                with st.spinner("Consultando base de datos NHTSA / Offline..."):
                    res_vin = tool_decodificar_vin.invoke(vin_input)
                    if isinstance(res_vin, dict) and "error" not in res_vin:
                        st.session_state.vin_decoded_data = res_vin
                        st.session_state.form_data["make"] = res_vin.get("make", "")
                        st.session_state.form_data["model"] = res_vin.get("model", "")
                        st.session_state.form_data["year"] = str(res_vin.get("year", ""))
                        st.session_state.form_data["vin"] = vin_input
                        st.session_state.form_data["vin_details"] = json.dumps(res_vin.get("details", {}), indent=2, ensure_ascii=False)
                        st.success(f"✅ VIN Decodificado: {res_vin.get('year')} {res_vin.get('make')} {res_vin.get('model')}")
                    else:
                        st.error(f"⚠️ Error al decodificar: {res_vin}")
            else:
                st.warning("El VIN debe contener exactamente 17 caracteres.")

        # Entradas manuales / editables
        c_yr, c_mk, c_md = st.columns([1, 1.5, 1.5])
        with c_yr:
            year_input = st.text_input("Año:", value=st.session_state.form_data.get("year", ""), placeholder="2018")
        with c_mk:
            make_input = st.text_input("Marca:", value=st.session_state.form_data.get("make", ""), placeholder="Honda / Acura")
        with c_md:
            model_input = st.text_input("Modelo:", value=st.session_state.form_data.get("model", ""), placeholder="Civic / TL")

        if st.session_state.vin_decoded_data:
            with st.expander("🔍 Especificaciones Técnicas del VIN"):
                st.json(st.session_state.vin_decoded_data)

    with col_veh_2:
        st.markdown("#### 2. Motivo de Falla / Síntomas")
        
        tipo_falla_idx = 0 if st.session_state.form_data.get("tipo_falla") == "DTC" else 1
        modo_falla = st.radio(
            "Método de diagnóstico disponible:",
            ["Código de Falla DTC (Con escáner OBD-II)", "Descripción de Síntomas (Sin escáner)"],
            index=tipo_falla_idx,
            horizontal=True
        )

        dtc_code_input = ""
        sintomas_input = ""

        if "Código de Falla" in modo_falla:
            dtc_code_input = st.text_input(
                "Código de Falla DTC (OBD-II):",
                value=st.session_state.form_data.get("dtc_code", ""),
                placeholder="Ej. P1106, P0300, P0171, P0420, C1904",
                help="Código estándar de 5 caracteres registrado por la ECU/PCM."
            ).strip().upper()
        else:
            sintomas_input = st.text_area(
                "Describe detalladamente el comportamiento del vehículo:",
                value=st.session_state.form_data.get("sintomas", ""),
                placeholder="Ej. El motor tiembla en ralentí, tira humo negro por el escape, cascabelea al acelerar y pierde potencia en subidas...",
                height=110
            ).strip()

    st.write("")

    btn_diagnosticar = st.button("🚀 Ejecutar Diagnóstico Experto SEDA", type="primary", use_container_width=True)

    if btn_diagnosticar:
        if not (year_input or make_input or model_input):
            st.warning("⚠️ Por favor ingresa al menos la Marca y Modelo del vehículo.")
        elif not (dtc_code_input or sintomas_input):
            st.warning("⚠️ Por favor ingresa un Código DTC o describe los Síntomas.")
        else:
            v_data = {
                "year": year_input,
                "make": make_input,
                "model": model_input,
                "dtc_code": dtc_code_input,
                "sintomas": sintomas_input,
                "vin_details": st.session_state.form_data.get("vin_details", "No disponible")
            }

            prog_bar = st.progress(0)
            status_placeholder = st.empty()

            def update_progress_form(step: int, msg: str, data: dict):
                prog_bar.progress(int(step * 25))
                status_placeholder.markdown(f"**Fase {step}/4:** {msg}")

            with st.spinner("Ejecutando pipeline multi-fuente SEDA..."):
                t_start = time.time()
                diag_res = execute_diagnostic_pipeline(
                    vehicle_data=v_data,
                    llm=active_llm,
                    progress_callback=update_progress_form
                )
                t_total = time.time() - t_start
                prog_bar.progress(100)
                status_placeholder.markdown(f"✅ **Diagnóstico completado exitosamente en {t_total:.2f} segundos.**")
                st.session_state.form_diagnosis_result = diag_res

    # Visualización de Resultados
    if st.session_state.form_diagnosis_result:
        res = st.session_state.form_diagnosis_result
        st.divider()
        st.markdown("## 📊 Resultados y Evidencia Técnica")

        sub_tab_rep, sub_tab_dtc, sub_tab_rag, sub_tab_parts, sub_tab_raw = st.tabs([
            "📄 Reporte del Ingeniero SEDA",
            "🏷️ Base de Datos OBD-II / FTS5",
            "📚 Manuales de Servicio (RAG)",
            "🛒 Refacciones & Mercado",
            "🔍 Parámetros Técnicos"
        ])

        with sub_tab_rep:
            if res.get("error"):
                st.error(f"⚠️ {res['error']}")
            
            if res.get("reporte_final"):
                st.markdown(res["reporte_final"])
                st.divider()
                st.download_button(
                    label="📥 Descargar Reporte (.md)",
                    data=res["reporte_final"],
                    file_name=f"Reporte_SEDA_{res['vehicle_data'].get('make')}_{res['vehicle_data'].get('dtc_code') or 'sintomas'}.md",
                    mime="text/markdown"
                )

        with sub_tab_dtc:
            st.markdown("#### Definición Oficial SAE")
            if res.get("dtc_exacto"):
                st.code(res["dtc_exacto"], language="yaml")
            else:
                st.info("Sin consulta directa de código SAE.")

            st.markdown("#### Contexto Experto / FTS5")
            if res.get("db_enriquecida"):
                st.json(res["db_enriquecida"])
            elif res.get("sintomas_encontrados"):
                st.json(res["sintomas_encontrados"])
            else:
                st.info("Sin contexto adicional FTS5.")

        with sub_tab_rag:
            st.markdown("#### Extractos de Manuales de Taller (ChromaDB)")
            if res.get("manuales_rag"):
                st.text_area("Fragmentos Recuperados:", value=res["manuales_rag"], height=300)
            else:
                st.info("No se encontraron coincidencias en los manuales indexados.")

        with sub_tab_parts:
            st.markdown("#### Búsqueda Web y Catálogo de Refacciones")
            col_ddg, col_ra = st.columns(2, gap="medium")
            with col_ddg:
                st.markdown("##### 🛒 Tiendas y Opciones en Línea (DuckDuckGo)")
                if res.get("refacciones_web"):
                    st.markdown(format_web_results(res["refacciones_web"]))
                else:
                    st.info("Sin resultados de búsqueda web.")
            with col_ra:
                st.markdown("##### 📦 Catálogo de Partes (RockAuto API)")
                if res.get("refacciones_rockauto"):
                    st.markdown(res["refacciones_rockauto"])
                else:
                    st.info("Consulta a catálogo RockAuto no ejecutada o sin coincidencias directas.")

        with sub_tab_raw:
            st.json(res.get("vehicle_data"))


# ==============================================================================
# MODO 2: CHAT ASISTENTE GUIADO (CONVERSACIÓN INTERACTIVA)
# ==============================================================================
with tab_chat:
    st.markdown("### 💬 Asistente Conversacional Guiado")
    st.caption("Diagnostica paso a paso conversando directamente con el Ingeniero Automotriz IA.")

    col_c_head, col_c_btn = st.columns([4, 1])
    with col_c_btn:
        if st.button("🔄 Reiniciar Chat", key="btn_reset_chat", use_container_width=True):
            st.session_state.chat_messages = []
            st.session_state.chat_step = "init"
            st.session_state.chat_vehicle_data = {
                "year": "",
                "make": "",
                "model": "",
                "dtc_code": "",
                "sintomas": "",
                "vin_details": "No disponible"
            }
            st.session_state.chat_diagnostic_result = None
            st.rerun()

    # Inicialización del mensaje de bienvenida
    if not st.session_state.chat_messages:
        bienvenida = (
            "👋 **¡Hola! Soy SEDA**, tu Sistema Experto en Diagnóstico Automotriz.\n\n"
            "Te ayudaré a diagnosticar la falla de tu auto consultando manuales de servicio oficiales, bases de datos OBD-II y refacciones compatibles.\n\n"
            "**Para comenzar:** ¿Cuentas con el **número VIN** de tu auto (17 caracteres) o prefieres ingresar **Año, Marca y Modelo** manualmente?"
        )
        st.session_state.chat_messages.append({"role": "assistant", "content": bienvenida})

    # Mostrar historial de chat
    for msg in st.session_state.chat_messages:
        avatar = "🚗" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # Botones rápidos para el paso inicial
    if st.session_state.chat_step == "init":
        st.write("**Opciones de inicio rápido:**")
        b1, b2, b3 = st.columns(3)
        if b1.button("🔑 Tengo número VIN", key="chat_opt_vin"):
            st.session_state.chat_step = "ask_vin"
            st.session_state.chat_messages.append({"role": "user", "content": "Cuento con el número VIN."})
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": "Excelente. Por favor ingresa los **17 caracteres del VIN**:"
            })
            st.rerun()

        if b2.button("📝 Ingresar Marca/Modelo manual", key="chat_opt_manual"):
            st.session_state.chat_step = "ask_manual_data"
            st.session_state.chat_messages.append({"role": "user", "content": "Prefiero ingresar los datos manualmente."})
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": "De acuerdo. Por favor escribe el **Año, Marca y Modelo** de tu vehículo (ej. *2000 Acura TL* o *2018 Honda Civic*):"
            })
            st.rerun()

        if b3.button("⚡ Caso de Prueba: Acura TL P1106", key="chat_opt_preset"):
            st.session_state.chat_vehicle_data = {
                "year": "2000",
                "make": "Acura",
                "model": "TL",
                "dtc_code": "P1106",
                "sintomas": "",
                "vin_details": "No disponible"
            }
            st.session_state.chat_step = "diagnosing"
            st.session_state.chat_messages.append({"role": "user", "content": "Quiero diagnosticar un Acura TL 2000 con código P1106."})
            st.rerun()

    # Input del Chat
    user_chat_input = st.chat_input("Escribe tu respuesta aquí...")

    if user_chat_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_chat_input})
        current_step = st.session_state.chat_step

        # Paso 1: Ingreso de VIN
        if current_step == "ask_vin":
            vin_clean = user_chat_input.strip().upper()
            if len(vin_clean) == 17:
                with st.spinner("Decodificando VIN..."):
                    res_vin = tool_decodificar_vin.invoke(vin_clean)
                    if isinstance(res_vin, dict) and "error" not in res_vin:
                        st.session_state.chat_vehicle_data["make"] = res_vin.get("make", "")
                        st.session_state.chat_vehicle_data["model"] = res_vin.get("model", "")
                        st.session_state.chat_vehicle_data["year"] = str(res_vin.get("year", ""))
                        st.session_state.chat_vehicle_data["vin_details"] = json.dumps(res_vin.get("details", {}), indent=2, ensure_ascii=False)
                        st.session_state.chat_step = "ask_problem"
                        
                        resp = (
                            f"✅ **Vehículo identificado:** {res_vin.get('year')} {res_vin.get('make')} {res_vin.get('model')}\n\n"
                            f"¿Cuentas con un **Código de Falla DTC** (ej. *P0300, P1106*) o deseas **describir los síntomas** del problema?"
                        )
                        st.session_state.chat_messages.append({"role": "assistant", "content": resp})
                    else:
                        st.session_state.chat_step = "ask_manual_data"
                        resp = f"⚠️ No se pudo decodificar el VIN por completo. Por favor, escribe directamente el **Año, Marca y Modelo**:"
                        st.session_state.chat_messages.append({"role": "assistant", "content": resp})
            else:
                if "manual" in user_chat_input.lower():
                    st.session_state.chat_step = "ask_manual_data"
                    resp = "Entendido. Escribe el **Año, Marca y Modelo** de tu vehículo:"
                else:
                    resp = "⚠️ El VIN debe tener 17 caracteres. Escribe el VIN correcto o escribe 'manual' para ingresar marca y modelo."
                st.session_state.chat_messages.append({"role": "assistant", "content": resp})
            st.rerun()

        # Paso 2: Ingreso Manual de Datos
        elif current_step == "ask_manual_data":
            tokens = user_chat_input.replace(",", " ").split()
            yr_val = ""
            for t in tokens:
                if t.isdigit() and len(t) == 4 and (1970 <= int(t) <= 2027):
                    yr_val = t
                    tokens.remove(t)
                    break
            
            mk_val = tokens[0] if len(tokens) > 0 else "Desconocida"
            md_val = " ".join(tokens[1:]) if len(tokens) > 1 else ""

            st.session_state.chat_vehicle_data["year"] = yr_val
            st.session_state.chat_vehicle_data["make"] = mk_val
            st.session_state.chat_vehicle_data["model"] = md_val
            st.session_state.chat_step = "ask_problem"

            resp = (
                f"🚗 Registrado: **{yr_val} {mk_val} {md_val}**.\n\n"
                f"¿Cuentas con un **Código DTC** de escáner (ej. *P0300, P1106*) o deseas **describir los síntomas** del vehículo?"
            )
            st.session_state.chat_messages.append({"role": "assistant", "content": resp})
            st.rerun()

        # Paso 3: Ingreso de Falla / Síntomas
        elif current_step == "ask_problem":
            clean_str = user_chat_input.strip().upper()
            dtc_match = re.search(r'\b[PCBU]\d{4}\b', clean_str)

            if dtc_match:
                st.session_state.chat_vehicle_data["dtc_code"] = dtc_match.group(0)
            else:
                st.session_state.chat_vehicle_data["sintomas"] = user_chat_input.strip()

            st.session_state.chat_step = "diagnosing"
            st.rerun()

        # Paso 4: Q&A Libre / Preguntas de Seguimiento
        elif current_step == "diagnosed":
            with st.spinner("SEDA está analizando tu consulta técnica con base en el diagnóstico..."):
                followup_ans = answer_followup_question(
                    question=user_chat_input,
                    diagnostic_context=st.session_state.chat_diagnostic_result,
                    chat_history=st.session_state.chat_messages,
                    llm=active_llm
                )
                st.session_state.chat_messages.append({"role": "assistant", "content": followup_ans})
            st.rerun()

    # Ejecución del diagnóstico si está en estado 'diagnosing'
    if st.session_state.chat_step == "diagnosing":
        with st.chat_message("assistant", avatar="🚗"):
            st.markdown("🔧 **Iniciando análisis del Sistema Experto SEDA...**")
            with st.spinner("Cruzando bases de datos SAE, manuales de taller y catálogo de partes..."):
                diag_result = execute_diagnostic_pipeline(
                    vehicle_data=st.session_state.chat_vehicle_data,
                    llm=active_llm
                )
                st.session_state.chat_diagnostic_result = diag_result
                st.session_state.chat_step = "diagnosed"

                report_text = diag_result.get("reporte_final") or f"⚠️ Error: {diag_result.get('error')}"
                
                final_chat_msg = (
                    f"### 📋 Reporte Técnico SEDA\n\n"
                    f"{report_text}\n\n"
                    f"---\n"
                    f"💡 *¿Tienes dudas sobre el diagnóstico, herramientas necesarias o refacciones? Pregúntame con total libertad.*"
                )
                st.session_state.chat_messages.append({"role": "assistant", "content": final_chat_msg})
        st.rerun()
