import sys
import json
sys.path.append('.')

from langchain_ollama import ChatOllama
from herramientas_seda import tool_busqueda_rockauto, tool_consulta_db_dtc

def inicializar_modelos():
    print("[CONFIG] Cargando motores de inferencia y herramientas...")
    #Modelo 1: Estricto, solo devuelve JSON para la extraccion de datos para las siguientes consultas que utilizaran las tools
    llm_json = ChatOllama(model="qwen2.5:3b", temperature=0.0, format="json")

    #Modelo 2: Cretativo, devuelve texto normal para poder redactar el reporte final
    llm_texto = ChatOllama(model="qwen2.5:3b", temperature=0.2)

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

    print("\n--- [FASE 3] Deducción de Categoría para RockAuto ---")

    prompt_categoria = f"""
    Basado en el siguiente diagnóstico (DTC), determina la categoría EXACTA para RockAuto.
    Usa estrictamente UNA de las siguientes opciones:
    - "Fuel & Air" (Para problemas de aire, presión atmosférica, BARO, MAP, MAF, inyectores de combustible).
    - "Ignition" (Para bobinas, bujías, fallos de encendido/misfire).
    - "Engine" (Para componentes mecánicos del bloque del motor, pistones).
    - "Cooling & Heating" (Para radiador, refrigerante, termostato).
    - "Exhaust & Emission" (Para sensores de oxígeno O2, catalizador).
    
    Descripción del DTC: {info_dtc}
    
    Responde ÚNICAMENTE con un objeto JSON con la llave "categoria".
    """
    res_categoria = llm_json.invoke(prompt_categoria)
    categoria = json.loads(res_categoria.content).get("categoria", "")
    print(f"Categoría deducida: {categoria}")

    print("\n--- [FASE 4] Búsqueda de Refacciones en API ---")
    # TÚ controlas el formato, no el LLM. Garantizamos que sea exactamente lo que la tool espera:
    query_rockauto = f"{datos.get('marca')}, {datos.get('anio')}, {datos.get('modelo')}, {categoria}"
    print(f"Query construida: '{query_rockauto}'")

    info_refacciones = tool_busqueda_rockauto.invoke(query_rockauto)

    print("\n--- [FASE 5] Generación de Reporte Final ---")
    prompt_final = f"""
    Eres SEDA, un Sistema Experto de Diagnóstico Automotriz profesional.
    
    REGLA DE ORO: PROHIBIDO INVENTAR O ALUCINAR DIAGNÓSTICOS. Tu respuesta debe basarse 100% en los "Datos Extraídos" proporcionados abajo. Si la información no menciona refrigeración, NO hables de refrigeración.
    
    DATOS EXTRAÍDOS DEL SISTEMA:
    
    - Vehículo: {datos.get('marca')} {datos.get('modelo')} {datos.get('anio')}
    - Falla reportada: {datos.get('codigo')}
    - Diagnóstico Oficial: {info_dtc}
    - Refacciones Encontradas: {info_refacciones}
    
    Consulta original del usuario: "{consulta_usuario}"
    
    Redacta un diagnóstico estructurado en: 1. Significado Técnico del Código, 2. Qué revisar, y 3. Refacciones sugeridas (con precios si los hay).
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