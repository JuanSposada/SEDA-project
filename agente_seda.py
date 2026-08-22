import sys
import json
sys.path.append('.')

from langchain_ollama import ChatOllama
from utils.tools_seda import (
    tool_consulta_db_dtc, 
    tool_buscar_refaccion_web, 
    tool_consultar_manuales,
    tool_decodificar_vin, 
    tool_buscar_por_sintomas,
    tool_consulta_dtc_enriquecida
)
from utils.llm_manager import get_llm

def collect_vehicle_data() -> dict:
    """
    Recolecta los datos del usuario de forma determinista (guiada)
    para evitar alucinaciones y asegurar contexto limpio.
    """
    print("\n" + "="*50)
    print("SISTEMA SEDA - INGRESO DE DATOS")
    print("="*50)

    has_vin = input("¿Cuentas con el número VIN del vehículo? (S/N): ").strip().upper()

    year, make, model = "", "", ""
    vin_details = "No disponible"

    if has_vin == 'S':
        vin = input("Ingresa los 17 caracteres del VIN: ").strip().upper()
        print("[Sistema] Decodificando VIN, por favor espera...")

        vin_response = tool_decodificar_vin.invoke(vin)

        if isinstance(vin_response, dict) and "error" not in vin_response:
            make = vin_response.get("make", "")
            model = vin_response.get("model", "")
            year = str(vin_response.get("year", ""))

            raw_details = vin_response.get("details", {})
            vin_details_json = json.dumps(raw_details, indent=2, ensure_ascii=False)
        
            print(f"\nVIN detectado exitosamente ({vin_response.get('estatus')})")
            if make or model or year:
                print(f"-> Vehículo detectado: {year} {make} {model}".strip())
        else:
            err_msg = vin_response.get("error") if isinstance(vin_response, dict) else vin_response
            print(f"⚠️ {err_msg}")

        # Solo pedimos los datos que hayan quedado vacíos (ej. si fue offline)
        print("\nPor favor, confirma o completa los datos del vehículo:")    
        if not year: year = input("No se detectó el Año. Ingresa el Año: ").strip()
        if not make: make = input("No se detectó la Marca. Ingresa la Marca: ").strip()
        if not model: model = input("No se detectó el Modelo. Ingresa el Modelo: ").strip()
        
    has_dtc = input("\n¿Cuentas con el código DTC (Código de Falla)? (S/N): ").strip().upper()

    dtc_code = ""
    sintomas_user = ""

    if has_dtc == 'S':
        dtc_code = input("\nIngresa el Código de Falla (Ej. P1106): ").strip().upper()
    else: 
        sintomas_user = input("Describe los síntomas del auto (Ej. tiembla mucho y tira humo negro): ").strip()

    return {
        "year": year,
        "make": make,
        "model": model,
        "dtc_code": dtc_code,
        "sintomas": sintomas_user,
        "vin_details": vin_details_json
    }

# Pipeline orquestador de respuestas

def run_seda_pipeline(llm, vehicle_data: dict):
    """
    Ejecuta el pipeline de RAG y herramientas. Solo se usa el LLM al final.
    """
    print("\n--- [FASE 1] Extracción de Datos del Vehículo ---")
    make = vehicle_data.get("make", "")
    model = vehicle_data.get("model", "")
    year = vehicle_data.get("year", "")
    dtc_code = vehicle_data.get("dtc_code", "")
    sintomas = vehicle_data.get("sintomas", "")
    vin_details = vehicle_data.get("vin_details", "No disponible")

    print("\n" + "="*55)
    print(" EJECUTANDO PIPELINE MULTI-FUENTE SEDA")
    print("="*55)

    info_db_exacta = ""
    info_db_enriquecida = ""
    codigo_referencia_rag = dtc_code

    #Fase 1: Busqueda Cruzada en Bases de Datos
    if dtc_code:
        print(f"\n--- [FASE 1] Consulta a base de datos de códigos DTC SAE y base de datos enriquecida para código {dtc_code} ---")

        # 1. Obtenemos la información exacta del código DTC desde la base de datos SAE
        info_db_exacta = tool_consulta_db_dtc.invoke({"codigo": dtc_code, "marca": make})

        # 2. Obtenemos información enriquecida del código DTC desde la base de datos interna que generamos por web Scrapping
        enriquecida_dict = tool_consulta_dtc_enriquecida.invoke({"codigo": dtc_code, "marca": make})
        info_db_enriquecida = json.dumps(enriquecida_dict, indent=2, ensure_ascii=False)
        
        print("-> Datos oficiales y contexto experto recopilados correctamente.")

    else:
        print(f"\n--- [FASE 1] Deducción Inteligente por Síntomas (Motor FTS5) ---")
        sintomas_info = tool_buscar_por_sintomas.invoke({"sintomas": sintomas, "marca": make})
        info_db_enriquecida = json.dumps(sintomas_info, indent=2, ensure_ascii=False)

        # MAGIA: Si dedujimos códigos probables, sacamos el #1 para investigarlo
        if "codigos_probables" in sintomas_info and len(sintomas_info["codigos_probables"]) > 0:
            codigo_referencia_rag = sintomas_info["codigos_probables"][0].get("codigo", "")
            print(f"-> Código principal deducido: {codigo_referencia_rag}")
            
            # Buscamos la descripción oficial de ese código que acabamos de deducir
            info_db_exacta = tool_consulta_db_dtc.invoke({"codigo": codigo_referencia_rag, "marca": make})
            print("-> Descripción oficial del código deducido obtenida.")


    #Fase 2: Busqueda RAG en base de conocimiento de ChromaDB (Manuales PDF)
    print("\n--- [FASE 2] Extrayendo diagramas y manuales oficiales (ChromaDB) ---")
    # Buscamos usando el código original o el deducido
    query_rag = f"{make} {model} {year} {codigo_referencia_rag} {sintomas}".strip()
    manuals_info = tool_consultar_manuales.invoke(query_rag)
    print("-> Documentación técnica extraída.")

    #Fase 3: Busqueda web de refacciones en (DuckDuckGo)
    print("\n--- [FASE 3] Consultando mercado de refacciones (DuckDuckGo) ---")
    web_query = f"{year} {make} {model} {codigo_referencia_rag} spare part"
    web_info = tool_buscar_refaccion_web.invoke(web_query)
    print("-> Opciones de mercado recopiladas.")

    #Fase 4: Sintetizar toda la información y generar respuesta final
    print("\n--- [FASE 4] Generación de Respuesta Final con Reporte Especializado---")
    print("[Sistema] El LLM está analizando y cruzando toda la información...")

    prompt_final = f"""
    Eres SEDA (Sistema Experto de Diagnóstico Automotriz), un Ingeniero Maestro automotriz altamente capacitado.
    
    === INFORMACIÓN PROPORCIONADA POR EL USUARIO ===
    - VEHÍCULO: {year} {make} {model}
    - TIPO DE CONSULTA: {'Búsqueda Directa por Código DTC' if dtc_code else 'Deducción por Síntomas'}
    - CÓDIGO DTC INGRESADO: {dtc_code if dtc_code else 'Ninguno (El usuario no cuenta con escáner)'}
    - SÍNTOMAS DESCRITOS: {sintomas if sintomas else 'Ninguno descrito'}

    === 1. ESPECIFICACIONES TÉCNICAS (VIN) ===
    {vin_details}

    === 2. DEFINICIÓN EXACTA (BD OFICIAL SAE) ===
    {info_db_exacta}

    === 3. CONTEXTO EXPERTO (BD ENRIQUECIDA / FTS5) ===
    {info_db_enriquecida}

    === 4. MANUALES TÉCNICOS LOCALES (RAG) ===
    {manuals_info}

    === 5. OPCIONES DE MERCADO WEB ===
    {web_info}

    INSTRUCCIONES Y REGLAS DE REDACCIÓN:
    1. RECONOCIMIENTO OBLIGATORIO: Inicia tu reporte mencionando el vehículo ({year} {make} {model}) y el código DTC ingresado ({dtc_code if dtc_code else 'Ninguno'}). Si la "BD Oficial SAE" indica que el código no se encontró, indícalo educadamente, pero **está estrictamente prohibido decir que el usuario no proporcionó un código si arriba dice lo contrario**.
    2. DIAGNÓSTICO LÓGICO: 
       - Si es búsqueda directa, explica qué significa el código y por qué se relaciona con el auto.
       - Si es por síntomas, explica los códigos probables que arrojó la base de datos FTS5.
    3. SEGURIDAD: Revisa el campo "puedo_manejarlo" y advierte sobre el riesgo de conducción.
    4. DOBLE GUÍA DE REPARACIÓN: Extrae consejos de "reparacion" para el dueño y pasos técnicos con valores para el taller.
    5. PREVENCIÓN: Menciona los "errores_comunes" para evitar cambios innecesarios de piezas.
    6. REFACCIONES: Sintetiza los precios y piezas de la web sin inventar enlaces.
    7. Formatea la respuesta estrictamente en Español usando Markdown.
    """

    response = llm.invoke(prompt_final)
    return response.content

if __name__ == "__main__":
    llm = get_llm()
    if not llm:
        print("Error: No se pudo inicializar el modelo de lenguaje. Verifica la configuración.")
        sys.exit(1)

    v_data = collect_vehicle_data()

    try:
        report = run_seda_pipeline(llm, v_data)
        print("\n" + "="*50)
        print("                 REPORTE DIAGNOSTICCO SEDA                  ")
        print("="*50)
        print(report)
        print("="*50)
    
    except Exception as e:
        print(f"\n❌ Error durante el pipeline: {str(e)}")