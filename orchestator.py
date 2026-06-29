import json
from pathlib import Path
from typing import List, Dict


# 1. Cargamos el mockup de la Base de conocimiento
def cargar_base_conocimiento(file_path: str) -> List[Dict]:
    ruta = Path(file_path)
    if not ruta.is_absolute():
        ruta = (Path(__file__).resolve().parent / ruta).resolve()

    with ruta.open('r', encoding='utf-8') as f:
        return json.load(f)


# 2. Motor de Busqueda de coincidencias (Inferencia basica)
def buscar_contexto_automotriz(entrada_usuario: str, base_conocimiento: List[Dict]) -> List[Dict]:
    coincidencias = []
    entrada_lowercase = entrada_usuario.lower()

    for item in base_conocimiento:
        # Busqueda por codigo OBD-II
        codigo_encontrado = any(codigo.lower() in entrada_lowercase for codigo in item.get("codigos_asociados", []))

        # Busqueda semantica simple por palabras clave de sintomas
        sintoma_encontrado = any(sintoma.lower() in entrada_lowercase for sintoma in item.get("sintomas_clave", []))

        if codigo_encontrado or sintoma_encontrado:
            coincidencias.append(item)

    return filtrar_por_vin(entrada_lowercase, coincidencias)


# 3. Filtro por VIN o marca/modelo (para asegurar la compatibilidad de refacciones)
def filtrar_por_vin(entrada_usuario: str, resultados: List[Dict]) -> List[Dict]:
    # Aqui se decodificara el codigo VIN
    # Por ahora, simulamos la deteccion de la marca en el texto del usuario
    marcas_disponibles = ["honda", "nissan", "toyota"]
    marca_detectada = None

    for marca in marcas_disponibles:
        if marca in entrada_usuario:
            marca_detectada = marca
            break

    if marca_detectada:
        compatibles = []
        for resultado in resultados:
            compatibilidad = resultado.get("compatibilidad", {})
            marca_compatibilidad = str(compatibilidad.get("marca", "")).lower()
            if marca_detectada in marca_compatibilidad or marca_detectada in entrada_usuario:
                compatibles.append(resultado)
        return compatibles

    return resultados

# 4. Diseño del Prompt Maestro para el Modelo Preentrenado
def generar_prompt_sistema_experto(entrada_usuario: str, contexto_json: List[Dict]) -> str:
    contexto_str = json.dumps(contexto_json, indent=2, ensure_ascii=False)

    prompt = f"""
    Eres un Sistema Experto en Diagnostico Automotriz e Inteligencia de Refacciones.
    Tu objetivo es guiar al ususario nncon un diagnostico tecnico impecable y sugerir las piezzas exactas que necesita.

    BASE DE CONOCIMIENTO LOCAL (INFORMACION REAL Y DISPONIBLE):
    {contexto_str}

    CONSULTA DEL USUARIO:
    '{entrada_usuario}'

    INSTRUCCIONES DE RAZONAMIENTO:
    1. Analiza los sintomas o codigos del usuario y contrastalos con la BASE DE CONOCIMIENTO LOCAL.
    2. Si hay coincidencias en la base de datos, utiliza el 'diagnostico_experto' y la 'prueba_sugerida' proporcionados para estructurar tu respuesta. No inventes procedimientos diferentes a los del contexto.
    3. Muestra lka informaciuon de refaccion compatible (Nombre, Numero de parte ejemplo y Precio aproximado).
    4. Si NO enciuentras informacion en la base de conocimiento local para esa falla especifica, utiliza tu conocimiento preentrenado general para dar un diagnostico tentativo, pero advierte claramente al usuario de que esa pieza no se encuentra actualmete en nuestro catalogo de refacciones.
    5. Manten un tono profesional, tecnico y de ingenieria.

    RESPUESTA ESTRUCTURADA:
    """
    return prompt

if __name__ == "__main__":
    base_datos = cargar_base_conocimiento('data/base_conocimiento.json')

    # Caso A: El usuario introduce sintomas y marca del carro
    entrada = "Tengo un nissan versa que tiembla mucho en los semaforos y avienta humo negro por el escape"

    print(f"--- Procesando Entrada: '{entrada}' ---")

    # El sistema busca en el JSON que refacciones mitigan esos sintomas
    contexto_encontrado = buscar_contexto_automotriz(entrada, base_datos)

    prompt_final = generar_prompt_sistema_experto(entrada, contexto_encontrado)

    print("\n-.- Prompt Generado para la IA -.-")
    print(prompt_final)