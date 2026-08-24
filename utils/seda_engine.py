import json
import sys
from pathlib import Path
from utils.tools_seda import (
    tool_consulta_db_dtc,
    tool_buscar_refaccion_web,
    tool_consultar_manuales,
    tool_decodificar_vin,
    tool_buscar_por_sintomas,
    tool_consulta_dtc_enriquecida,
    tool_busqueda_rockauto
)
from utils.llm_manager import get_llm

def _format_vin_specs(vin_raw) -> str:
    """Extrae únicamente los campos mecánicos relevantes del VIN para evitar ruido y consumo excesivo de tokens."""
    if not vin_raw or vin_raw == "No disponible":
        return "No disponible (Datos del vehículo ingresados manualmente)."
    
    try:
        data = json.loads(vin_raw) if isinstance(vin_raw, str) else vin_raw
        if not isinstance(data, dict):
            return str(vin_raw)

        # Si el dict contiene 'details', desempaquetar
        details = data.get("details", data) if isinstance(data.get("details"), dict) else data

        campos_clave = []
        if details.get("Make"): campos_clave.append(f"- Fabricante: {details.get('Make')} ({details.get('Manufacturer Name', '')})")
        if details.get("Model Year"): campos_clave.append(f"- Año / Modelo: {details.get('Model Year')} {details.get('Model', '')}")
        
        motor = details.get("Engine Model", "")
        cilindros = details.get("Engine Number of Cylinders", "")
        valvulas = details.get("Valve Train Design", "")
        hp = details.get("Engine Brake (hp) From", "")
        
        motor_desc = []
        if motor: motor_desc.append(f"Modelo {motor}")
        if cilindros: motor_desc.append(f"{cilindros} Cilindros")
        if valvulas: motor_desc.append(valvulas)
        if hp: motor_desc.append(f"{hp} HP")
        if motor_desc:
            campos_clave.append(f"- Motor: {', '.join(motor_desc)}")

        if details.get("Drive Type"): campos_clave.append(f"- Tracción: {details.get('Drive Type')}")
        if details.get("Fuel Type - Primary"): campos_clave.append(f"- Combustible: {details.get('Fuel Type - Primary')}")
        if details.get("Plant Country"): campos_clave.append(f"- País de Ensamble: {details.get('Plant Country')}")

        if campos_clave:
            return "\n".join(campos_clave)
        return "Especificaciones básicas decodificadas."
    except Exception:
        return "No disponible"


def execute_diagnostic_pipeline(vehicle_data: dict, llm=None, progress_callback=None) -> dict:
    """
    Ejecuta el pipeline multi-fuente SEDA (DTC/FTS5 + RAG + Web/RockAuto + LLM).
    """
    make = vehicle_data.get("make", "").strip()
    model = vehicle_data.get("model", "").strip()
    year = str(vehicle_data.get("year", "")).strip()
    dtc_code = vehicle_data.get("dtc_code", "").strip().upper()
    sintomas = vehicle_data.get("sintomas", "").strip()
    vin_details_raw = vehicle_data.get("vin_details", "No disponible")
    vin_specs_clean = _format_vin_specs(vin_details_raw)

    resultado = {
        "vehicle_data": vehicle_data,
        "dtc_exacto": "",
        "db_enriquecida": {},
        "sintomas_encontrados": {},
        "codigo_referencia": dtc_code,
        "manuales_rag": "",
        "refacciones_web": "",
        "refacciones_rockauto": "",
        "reporte_final": "",
        "error": None
    }

    # ==========================================
    # FASE 1: Búsqueda Cruzada en Bases de Datos
    # ==========================================
    if progress_callback:
        progress_callback(1, "Consultando base de datos SAE y contexto experto FTS5...", {})

    info_db_exacta = ""
    info_db_enriquecida_str = ""
    codigo_referencia_rag = dtc_code

    try:
        if dtc_code:
            # 1. Base SAE
            info_db_exacta = tool_consulta_db_dtc.invoke({"codigo": dtc_code, "marca": make})
            resultado["dtc_exacto"] = info_db_exacta

            # 2. Base enriquecida
            enriquecida_dict = tool_consulta_dtc_enriquecida.invoke({"codigo": dtc_code})
            resultado["db_enriquecida"] = enriquecida_dict
            info_db_enriquecida_str = json.dumps(enriquecida_dict, indent=2, ensure_ascii=False)
        else:
            # Deducción por síntomas FTS5
            sintomas_info = tool_buscar_por_sintomas.invoke({"sintomas": sintomas, "marca": make})
            resultado["sintomas_encontrados"] = sintomas_info
            info_db_enriquecida_str = json.dumps(sintomas_info, indent=2, ensure_ascii=False)

            if isinstance(sintomas_info, dict) and "codigos_probables" in sintomas_info and len(sintomas_info["codigos_probables"]) > 0:
                codigo_referencia_rag = sintomas_info["codigos_probables"][0].get("codigo", "")
                resultado["codigo_referencia"] = codigo_referencia_rag
                info_db_exacta = tool_consulta_db_dtc.invoke({"codigo": codigo_referencia_rag, "marca": make})
                resultado["dtc_exacto"] = info_db_exacta

    except Exception as e:
        resultado["error"] = f"Error en Fase 1 (Bases de datos): {str(e)}"

    # ==========================================
    # FASE 2: Búsqueda RAG en Manuales Técnicos
    # ==========================================
    if progress_callback:
        progress_callback(2, "Buscando diagramas y especificaciones en manuales de taller (ChromaDB RAG)...", {})

    manuals_info = ""
    try:
        query_rag = f"{make} {model} {year} {codigo_referencia_rag} {sintomas}".strip()
        manuals_info = tool_consultar_manuales.invoke(query_rag)
        resultado["manuales_rag"] = manuals_info
    except Exception as e:
        manuals_info = f"[Aviso RAG] No se pudo consultar ChromaDB: {str(e)}"
        resultado["manuales_rag"] = manuals_info

    # ==========================================
    # FASE 3: Búsqueda de Refacciones (Web & RockAuto)
    # ==========================================
    if progress_callback:
        progress_callback(3, "Localizando refacciones y opciones de mercado en tiempo real...", {})

    web_info = ""
    rockauto_info = ""
    try:
        # Extraer término clave de pieza
        componentes_clave = ""
        if "Description:" in info_db_exacta:
            desc_line = [l for l in info_db_exacta.split("\n") if "Description:" in l]
            if desc_line:
                componentes_clave = desc_line[0].replace("Description:", "").strip()

        web_search_term = componentes_clave if componentes_clave else (codigo_referencia_rag if codigo_referencia_rag else sintomas)
        web_query = f"{year} {make} {model} {web_search_term} spare part".strip()
        web_info = tool_buscar_refaccion_web.invoke(web_query)
        resultado["refacciones_web"] = web_info

        # Intento de RockAuto si hay datos suficientes
        if make and year and model and web_search_term:
            try:
                ra_param = f"{make}, {year}, {model}, {web_search_term}"
                rockauto_info = tool_busqueda_rockauto.invoke(ra_param)
                resultado["refacciones_rockauto"] = rockauto_info
            except Exception:
                pass
    except Exception as e:
        web_info = f"[Aviso Refacciones] {str(e)}"
        resultado["refacciones_web"] = web_info

    # ==========================================
    # FASE 4: Síntesis con LLM y Reporte Maestro
    # ==========================================
    if progress_callback:
        progress_callback(4, "El Ingeniero Maestro LLM está generando el reporte de diagnóstico estructurado...", {})

    if llm is None:
        llm = get_llm()

    if not llm:
        resultado["error"] = "No se pudo inicializar el modelo de lenguaje (Hugging Face / Ollama)."
        return resultado

    prompt_final = f"""
    Eres SEDA (Sistema Experto de Diagnóstico Automotriz), un Ingeniero Automotriz Maestro de nivel senior.
    Tu objetivo es emitir un reporte de diagnóstico técnico exhaustivo, profesional y completo, siguiendo OBLIGATORIAMENTE la estructura indicada.
    
    === DATOS DE ENTRADA DEL CASO ===
    - VEHÍCULO: {year} {make} {model}
    - MODALIDAD: {'Búsqueda Directa por Código DTC' if dtc_code else 'Deducción por Síntomas'}
    - CÓDIGO DTC INGRESADO: {dtc_code if dtc_code else 'Ninguno'}
    - SÍNTOMAS REPORTADOS: {sintomas if sintomas else 'Ninguno'}
    - ESPECIFICACIONES (VIN):
{vin_specs_clean}

    === CONTEXTO TÉCNICO RECUPERADO DE LAS BASES DE DATOS ===
    [1. DEFINICIÓN OFICIAL SAE]:
    {info_db_exacta}

    [2. CONTEXTO EXPERTO / FTS5]:
    {info_db_enriquecida_str}

    [3. MANUALES DE SERVICIO LOCALES (RAG)]:
    {manuals_info}

    [4. MERCADO Y REFACCIONES]:
    {web_info}
    {rockauto_info}

    === FORMATO OBLIGATORIO DEL REPORTE ===
    Genera el reporte EXACTAMENTE con los siguientes títulos de sección y en Español profesional:

    # 🚗 Reporte de Diagnóstico SEDA: {year} {make} {model}

    ## 1. 🔍 Resumen del Diagnóstico y Código de Falla
    - **Código / Falla Identificada:** (Menciona el código DTC oficial o deducido y su descripción SAE)
    - **Causa Raíz Principal:** (Explica técnicamente qué componente o circuito está fallando con base en la evidencia)
    - **Ficha del Vehículo:** (Menciona motor, tracción y especificaciones detectadas)

    ## 2. ⚠️ Evaluación de Seguridad y Manejo del Vehículo
    - **¿Es seguro conducirlo?:** (Indica 'Sí', 'Con Precaución' o 'No Conducir' y fundamenta el porqué basándote en 'puedo_manejarlo')
    - **Riesgos de Daño Mayor:** (Advierte sobre posibles daños a catalizador, transmisión o motor si no se atiende)

    ## 3. 🛠️ Guía Paso a Paso de Pruebas y Reparación
    - **Inspección Básica (Para el Conductor):** (Revisiones visuales de arneses, fusibles, mangueras o fugas)
    - **Procedimiento de Taller (Técnico Automotriz):** (Pruebas con multímetro, voltajes o mediciones extraídas de los manuales RAG)

    ## 4. 🛒 Refacciones y Componentes Compatibles
    (Presenta una tabla o lista con las piezas necesarias, números de parte y fuentes de mercado detectadas en la búsqueda web o RockAuto. Si no hay precio exacto, indica consultar refaccionaria local).

    ## 5. 💡 Conclusión y Recomendación del Ingeniero
    (Resumen ejecutivo con los siguientes pasos prioritarios para resolver la falla).
    """

    try:
        response = llm.invoke(prompt_final)
        resultado["reporte_final"] = response.content
    except Exception as e:
        resultado["error"] = f"Error al generar reporte con el LLM: {str(e)}"

    return resultado


def answer_followup_question(question: str, diagnostic_context: dict, chat_history: list, llm=None) -> str:
    """
    Responde preguntas de seguimiento en el modo Chat manteniendo el contexto del diagnóstico previo.
    """
    if llm is None:
        llm = get_llm()

    if not llm:
        return "Error: No se pudo conectar con el modelo de lenguaje."

    v_data = diagnostic_context.get("vehicle_data", {})
    reporte_previo = diagnostic_context.get("reporte_final", "")
    manuales = diagnostic_context.get("manuales_rag", "")

    # Historial reciente
    historial_str = ""
    for msg in chat_history[-6:]:
        rol = "Usuario" if msg.get("role") == "user" else "SEDA"
        historial_str += f"{rol}: {msg.get('content')}\n"

    prompt_chat = f"""
    Eres SEDA (Sistema Experto de Diagnóstico Automotriz). Estás conversando con el usuario respondiendo dudas sobre el diagnóstico previo de su vehículo.

    === CONTEXTO DEL VEHÍCULO Y DIAGNÓSTICO PREVIO ===
    - Vehículo: {v_data.get('year')} {v_data.get('make')} {v_data.get('model')}
    - Código DTC / Falla: {v_data.get('dtc_code') or v_data.get('sintomas')}
    
    === REPORTE DE DIAGNÓSTICO EMITIDO ===
    {reporte_previo}

    === MANUALES TÉCNICOS DISPONIBLES ===
    {manuales}

    === HISTORIAL DE LA CONVERSACIÓN ===
    {historial_str}

    === NUEVA PREGUNTA DEL USUARIO ===
    "{question}"

    INSTRUCCIONES:
    1. Responde de forma clara, técnica, precisa y servicial en Español.
    2. Si el usuario pregunta por herramientas, procedimientos o seguridad, apóyate en el diagnóstico y manuales previos.
    3. Si la pregunta requiere información no existente en el contexto, indícalo con honestidad profesional sin inventar datos.
    4. Sé conciso y utiliza formato Markdown.
    """

    try:
        response = llm.invoke(prompt_chat)
        return response.content
    except Exception as e:
        return f"Ocurrió un error al procesar tu consulta: {str(e)}"
