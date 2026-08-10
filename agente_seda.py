import sys
import json
sys.path.append('.')

from langchain_ollama import ChatOllama
from utils.tools_seda import (
    tool_consulta_db_dtc, 
    tool_buscar_refaccion_web, 
    tool_consultar_manuales,
    tool_decodificar_vin
)
from utils.llm_manager import obtener_llm

def collect_vehicle_data() -> dict:
    print("\n" + "="*50)
    print("SISTEMA SEDA - INGRESO DE DATOS")
    print("="*50)

    has_vin = input("¿Cuentas con el número VIN del vehículo? (S/N): ").strip().upper()

    year, make, model = "", "", ""
    vin_details = "No disponible"

    if has_vin == 'S':
        vin = input("Ingresa los 17 caracteres del VIN: ").strip().upper()
        print("[Sistema] Decodificando VIN, por favor espera...")

        vin_results = tool_decodificar_vin.invoke(vin)

        if "error" not in vin_results:
            make = vin_results.get("make", "")
            model = vin_results.get("model", "")
            year = vin_results.get("year", "")
            vin_details = json.dumps(vin_results.get("details", {}), indent=2)
        
            print(f"\nVIN detectado exitosamente ({vin_results.get('estatus')})")
            print(f"Auto-detectado: {year} {model} {make}")

            # Solo pedimos los datos que hayan quedado vacíos (ej. si fue offline)
            if not year: year = input("No se detectó el Año. Ingresa el Año: ").strip()
            if not make: make = input("No se detectó la Marca. Ingresa la Marca: ").strip()
            if not model: model = input("No se detectó el Modelo. Ingresa el Modelo: ").strip()
        else:
            print(f"{vin_results['error']}")
            # Fallback manual si el VIN era inválido
            year = input("Ingresa el Año: ").strip()
            make = input("Ingresa la Marca: ").strip()
            model = input("Ingresa el Modelo: ").strip()

    dtc_code = input("\nIngresa el Código de Falla (Ej. P1106): ").strip().upper()

    return {
        "year": year,
        "make": make,
        "model": model,
        "dtc_code": dtc_code,
        "vin_details": vin_details
    }

# Pipeline orquestador de respuestas

def run_seda_pipeline(llm, vehicle_data: dict):
    print("\n--- [FASE 1] Extracción de Datos del Vehículo ---")
    make = vehicle_data.get("make", "")
    model = vehicle_data.get("model", "")
    year = vehicle_data.get("year", "")
    dtc_code = vehicle_data.get("dtc_code", "")
    vin_details = vehicle_data.get("vin_details", "No disponible")

    print("\n" + "="*55)
    print(" EJECUTANDO PIPELINE MULTI-FUENTE SEDA")
    print("="*55)

    #Fase 1: Consuolta de SQLite para la base de Datos de DTC definitions
    print("\n--- [FASE 1] Consutla a base de datos de codigos DTC (SQLite) ---")
    dtc_info = tool_consulta_db_dtc.invoke({"codigo": dtc_code, "marca": make})
    print("-> Definición del código recuperada.")

    #Fase 2: Busqueda RAG en base de conocimiento de ChromaDB
    print("\n--- [FASE 2] Consulta a Base de Conocimiento RAG (ChromaDB) ---")
    rag_query = f"{make} {model} {year} {dtc_code}"
    manuals_info = tool_consultar_manuales.invoke(rag_query)
    print("-> Información de manuales técnicos recuperada.")

    #Fase 3: Busqueda web de refacciones en (DuckDuckGo)
    print("\n--- [FASE 3] Búsqueda de Refacciones en línea (DuckDuckGo) ---")
    search_query = f"{make} {model} {year} {dtc_code} spare part"
    web_info = tool_buscar_refaccion_web.invoke(search_query)
    print("-> Resultados de búsqueda de refacciones recuperados.")

    #Fase 4: Sintetizar toda la información y generar respuesta final
    print("\n--- [FASE 4] Generación de Respuesta Final con Reporte Especializado---")

    prompt_final = f"""
    Eres SEDA (Sistema Experto de Diagnóstico Automotriz), un asistente técnico para mecánicos y técnicos automotrices. Tu objetivo es generar un diagnóstico claro, técnicamente riguroso y útil.

    DATOS PRINCIPALES DEL VEHÍCULO:
    - Marca: {make}
    - Modelo: {model}
    - Año: {year}
    - Código DTC registrado: {dtc_code}

    === ESPECIFICACIONES TÉCNICAS DEL VIN (JSON) ===
    {vin_details}

    === INFORMACIÓN DEL CÓDIGO DTC (Base de Datos) ===
    {dtc_info}

    === EXTRACTOS TÉCNICOS RECUPERADOS DE MANUALES DE TALLER ===
    {manuals_info}

    === RESULTADOS DE BÚSQUEDA WEB PARA REFACCIONES ===
    {web_info}

    INSTRUCCIONES Y REGLAS ESTRICTAS DE REDACCIÓN:
    1. IDIOMA Y TONO: Responde EXCLUSIVAMENTE en español con un lenguaje técnico, claro y profesional.
    2. SÍNTESIS Y COPYRIGHT: Está PROHIBIDO copiar textualmente los fragmentos de los manuales. Sintetiza, parafrasea y explica los procedimientos con tus propias palabras.
    3. ESPECIFICACIONES TÉCNICAS: Usa los detalles del VIN (tipo de motor, cilindrada, tracción) si modifican el procedimiento de revisión o las pruebas eléctricas.
    4. MAPEO DE SUBMARCAS: Considera las submarcas y variantes de modelos (ej. Scion -> Toyota) para asegurar compatibilidad con el codigo DTC y compativbilidad de refacciones.
    4. CITACIÓN ÉTICA: Si los extractos del manual indican páginas o archivos fuente, no lo cites, solo contruye respuesta en base a la infromacion.
    5. REFACCIONES: Recomienda los repuestos necesarios integrando las alternativas o precios encontrados en la web. INCLUYE los enlaces a proveedores si están disponibles. Si no hay datos claros, indícalo explícitamente sin inventar enlaces.

    ESTRUCTURA DEL REPORTE FINAL:
    1. Resumen del Vehículo y Falla Identificada
    2. Descripción Técnica del Código DTC
    3. Procedimiento de Inspección y Pruebas Sugeridas
    4. Opciones de Refacciones y Sugerencias de Compra
    """

    response = llm.invoke(prompt_final)
    return response.content

if __name__ == "__main__":
    llm = obtener_llm()
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