import json
from huggingface_hub import InferenceClient
from typing import List, Dict

# 1. Inicializar el cliente gratuito de Hugging Face
# Reemplaza con tu token generado en la plataforma
HF_TOKEN = "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"

# Usamos el modelo open-source de Meta, ideal para seguir instrucciones y prompts estructurados
client = InferenceClient(model="meta-llama/Meta-Llama-3-8B-Instruct", token=HF_TOKEN)

def cargar_base_conocimiento(archivo_path: str) -> List[Dict]:
    with open(archivo_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def buscar_contexto_automotriz(entrada_usuario: str, base_conocimiento: List[Dict]) -> List[Dict]:
    coincidencias = []
    entrada_lowercase = entrada_usuario.lower()
    
    for item in base_conocimiento:
        codigo_encontrado = any(codigo.lower() in entrada_lowercase for codigo in item["codigos_asociados"])
        sintoma_encontrado = any(sintoma.lower() in entrada_lowercase for sintoma in item["sintomas_clave"])
        
        if codigo_encontrado or sintoma_encontrado:
            coincidencias.append(item)
            
    return filtrar_por_compatibilidad(entrada_lowercase, coincidencias)

def filtrar_por_compatibilidad(entrada_usuario: str, resultados: List[Dict]) -> List[Dict]:
    marcas_disponibles = ["honda", "nissan", "toyota"]
    marca_detectada = None
    
    for marca in marcas_disponibles:
        if marca in entrada_usuario:
            marca_detectada = marca
            break
            
    if marca_detectada:
        return [r for r in resultados if r["compatibilidad"]["marca"].lower() == marca_detectada]
    
    return resultados

# === FUNCIÓN ADAPTADA PARA HUGGING FACE ===
def consultar_sistema_experto_hf(entrada_usuario: str, contexto_json: List[Dict]) -> str:
    # 1. Convertimos el JSON filtrado a string
    contexto_str = json.dumps(contexto_json, indent=2, ensure_ascii=False)
    
    # 2. Definimos las reglas del sistema experto
    system_prompt = """
    Eres un Sistema Experto Automotriz de base fáctica estricta. Tu única fuente de verdad es la BASE DE CONOCIMIENTO LOCAL (JSON) proporcionada. 

    REGLAS DE ORO QUE NO PUEDES ROMPER:
    1. Si la consulta del usuario coincide con los 'sintomas_clave' o 'codigos_asociados' de algún elemento del JSON, estás OBLIGADO a usar EXCLUSIVAMENTE el 'diagnostico_experto', la 'prueba_sugerida' y la 'info_refaccion' de ESE elemento específico.
    2. Prohibido inventar refacciones, precios o números de parte que no existan textualmente en el JSON provisto.
    3. Si encuentras la pieza en el JSON, NO muestres el mensaje de '⚠️ Nota: Este diagnóstico es preliminar...'. Ese mensaje es ÚNICAMENTE si el JSON viene completamente vacío [].
    4. Sé breve, directo y estructurado.
    """

    # 3. Formateamos el mensaje del usuario con la base de datos
    user_prompt = f"""
    BASE DE CONOCIMIENTO LOCAL:
    {contexto_str}

    CONSULTA DEL USUARIO:
    "{entrada_usuario}"

    Por favor, genera el diagnóstico estructurado:
    """

    # 4. Cambiamos 'text_generation' por 'chat_completion' para cumplir con la API
    response = client.chat_completion(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=800,
        temperature=0.2
    )
    
    # Retornamos el contenido del mensaje de texto generado
    return response.choices[0].message.content

# --- PRUEBA DEL SISTEMA ---
if __name__ == "__main__":
    base_datos = cargar_base_conocimiento('data/base_conocimiento.json')
    
    entrada = "Tengo un Honda Civic que tiembla mucho cuando lo prendo en las mañanas y se me jalonea al acelerar"
    
    print("1. Buscando fallas y refacciones compatibles...")
    contexto_filtrado = buscar_contexto_automotriz(entrada, base_datos)
    
    print(f"2. Enviando contexto a la IA de Hugging Face...")
    respuesta = consultar_sistema_experto_hf(entrada, contexto_filtrado)
    
    print("\n================ RESPUESTA DEL SISTEMA EXPERTO (HF) ================")
    print(respuesta)
    print("====================================================================")