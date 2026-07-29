import sys
import json
sys.path.append('.')

from langchain_ollama import ChatOllama
from herramientas_seda import tool_busqueda_rockauto, tool_consulta_db_dtc

LLM_MODEL = "qwen2.5:3b"  # Modelo de inferencia para el pipeline

def inicializar_modelos():
    print(f"[CONFIG] Cargando motores de inferencia({LLM_MODEL}) y herramientas...")
    #Modelo 1: Estricto, solo devuelve JSON para la extraccion de datos para las siguientes consultas que utilizaran las tools
    llm_json = ChatOllama(model=LLM_MODEL, temperature=0.0, format="json")

    #Modelo 2: Cretativo, devuelve texto normal para poder redactar el reporte final
    llm_texto = ChatOllama(model=LLM_MODEL, temperature=0.1)

    return llm_json, llm_texto

def pipeline_diagnostico_seda(llm_json, llm_texto, consulta_usuario):
    print("\n--- [FASE 1] Extracción de Datos del Vehículo ---")
    prompt_extraccion = f"""
    Extrae la información del vehículo de la siguiente consulta.
    REGLA ESTRICTA: 'marca' es el fabricante (ej. Acura, Honda, Nissan). 'modelo' es el nombre del carro (ej. TL, Civic, Sentra).
    Si el usuario dice "Acura TL", marca="Acura", modelo="TL".
    
    Consulta: "{consulta_usuario}"
    
    Responde ÚNICAMENTE con un objeto JSON con las llaves: "codigo", "marca", "modelo", "anio".
    """
    
    res_extraccion = llm_json.invoke(prompt_extraccion)
    datos = json.loads(res_extraccion.content)
    
    #Si el LLM falla en separar marca y modelo se extrae del mismo
    marca = datos.get("marca", "").strip()
    modelo = datos.get("modelo", "").strip()
    if not marca and " " in modelo:
        marca, modelo = modelo.split(" ", 1)
        datos["marca"] = marca
        datos["modelo"] = modelo
    
    print(f"Datos extraídos: {datos}")

    print("\n--- [FASE 2] Consulta a Base de Datos Local ---")

    # Ejecutamos la herramienta con los datos limpios extraídos
    info_dtc = tool_consulta_db_dtc.invoke({
        "codigo": datos.get("codigo", ""),
        "marca": datos.get("marca", "")
    })

    print(info_dtc.split('\n')[1]) # Imprime solo un resumen para la consola

    # Preduagnostico para que el modelo no alucine al buscar las refacciones y se base en la información extraida del DTC y no en suposiciones
    print("\n--- [FASE 3] Identificación del Componente Defectuoso ---")
    prompt_analisis = f"""
    Eres un analizador técnico automotriz estricto. Tu tarea es extraer e identificar el nombre técnico exacto de la refacción o sensor físico en inglés.

    DICCIONARIO TÉCNICO DE REFERENCIA:
    - "BARO" o "Barometric" -> "MAP Sensor"
    - "MAF" o "Mass Air Flow" -> "MAF Sensor"
    - "O2" o "HO2S" -> "Oxygen Sensor"
    - "EGR" -> "EGR Valve"
    - "CKP" -> "Crankshaft Position Sensor"
    - "CMP" -> "Camshaft Position Sensor"
    - "TPS" -> "Throttle Position Sensor"

    Texto a analizar: "{info_dtc}"

    Responde ÚNICAMENTE con un objeto JSON con la llave "componente" especificando el nombre de la pieza en inglés.
    Ejemplo: {{"componente": "MAP Sensor"}}
    """
    res_analisis = llm_json.invoke(prompt_analisis)
    analisis_mecanico = json.loads(res_analisis.content)
    componente_detectado = analisis_mecanico.get("componente", "MAP Sensor")
    print(f"-> Componente aislado por el LLM: {componente_detectado}")
          
    print("\n--- [FASE 4] Búsqueda de Refacciones en API ---")
    
    # TÚ controlas el formato, no el LLM. Garantizamos que sea exactamente lo que la tool espera:
    query_rockauto = f"{datos.get('marca')}, {datos.get('anio')}, {datos.get('modelo')}, {componente_detectado}"
    print(f"Query construida: '{query_rockauto}'")

    info_refacciones = tool_busqueda_rockauto.invoke(query_rockauto)

    print("\n--- [FASE 5] Generación de Reporte Final ---")
    prompt_final = f"""
    Eres SEDA, un Sistema Experto de Diagnóstico Automotriz.
    
    INFORMACIÓN OFICIAL DEL SISTEMA:
    - Vehículo: {datos.get('marca')} {datos.get('modelo')} {datos.get('anio')}
    - Código DTC: {datos.get('codigo')}
    - Descripción Oficial: {info_dtc}
    - Componente Defectuoso: {componente_detectado}
    - Resultado de Refacciones en RockAuto:
      {info_refacciones}
    
    REGLAS DE ORO (INVIOLABLES):
    1. El código P1106 en Acura/Honda corresponde al sensor de presión barométrica / colector (BARO / MAP Sensor). NO TIENE NADA QUE VER CON SISTEMAS DE FRENOS O ABS.
    2. SI "Resultado de Refacciones" contiene "Error" o "No se localizó", DEBES DECLARAR EXPRESAMENTE: "No se encontraron refacciones disponibles en línea para este modelo."
    3. ¡QUEDA ESTRICTAMENTE PROHIBIDO INVENTAR NOMBRES DE RECAMBIOS O ENLACES URL! Solo copia los enlaces que aparezcan textualmente dentro del resultado de RockAuto. Si no hay enlaces en el resultado, NO generes ningún enlace.
    4. Responde en español profesional.
    
    Consulta original del usuario: "{consulta_usuario}"
    
    Redacta un diagnóstico estructurado en: 
    1. Significado Técnico del Código 
    2. Componente Defectuoso e Importancia
    3. Síntomas comunes
    4. Qué revisar en el taller
    5. Refacciones sugeridas (con enlaces exactos del sistema si los hay).
    """

    respuesta_final = llm_texto.invoke(prompt_final)

    return respuesta_final.content

if __name__ == "__main__":
    llm_json, llm_texto = inicializar_modelos()
    consulta_prueba = "Tengo un Acura TL 2000 con el código de falla P1106. ¿Qué significa y qué repuestos necesito?"
    print("\n" + "="*50)
    print(f" Lanzando consulta: '{consulta_prueba}'")
    print("="*50)

    try:
        diagnostico = pipeline_diagnostico_seda(llm_json, llm_texto, consulta_prueba)
        print("\n" + "="*50)
        print("                 RESPUESTA FINAL                  ")
        print("="*50)
        print(diagnostico)
    except Exception as e:
        print(f"\n❌ Error durante el pipeline: {str(e)}")