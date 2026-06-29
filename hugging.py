import json
from sentence_transformers import SentenceTransformer, util





with open("data/base_conocimiento.json", "r", encoding="utf-8") as f:
    base_conocimiento = json.load(f)

# Cargar modelo gratuito
model = SentenceTransformer("all-MiniLM-L6-v2")

entrada_usuario = "Tengo un Nissan Versa que tiembla mucho en los semáforos y avienta humo negro por el escape"
entrada_emb = model.encode(entrada_usuario, convert_to_tensor=True)

# Detectar marca y modelo en la entrada
entrada_lower = entrada_usuario.lower()
marca_detectada = None
modelo_detectado = None

for item in base_conocimiento: 
    comp = item.get("compatibilidad", {})
    marca = comp.get("marca", "").lower()
    modelo = comp.get("modelo", "").lower()

    if marca in entrada_lower:
        marca_detectada = marca
    if modelo in entrada_lower:
        modelo_detectado = modelo

resultados = [] 

for item in base_conocimiento:
    comp = item.get("compatibilidad", {})
    marca = comp.get("marca", "").lower()
    modelo = comp.get("modelo", "").lower()

    # Filtrar por marca y modelo detectados
    if marca_detectada and marca != marca_detectada:
        continue
    if modelo_detectado and modelo != modelo_detectado:
        continue

    sintomas_texto = " ".join(item["sintomas_clave"])
    sint_emb = model.encode(sintomas_texto, convert_to_tensor=True)
    score = util.cos_sim(entrada_emb, sint_emb).item()
    resultados.append((item["componente"], score, item))


# Ordenar por similitud
resultados.sort(key=lambda x: x[1], reverse=True)

# Mostrar el más probable
if resultados:
    mejor = resultados[0][2]
    print("Diagnóstico sugerido:", mejor["diagnostico_experto"]["causa_raiz"])
    print("Prueba sugerida:", mejor["diagnostico_experto"]["prueba_sugerida"])
    print("Refacción:", mejor["info_refaccion"]["numero_parte_ejemplo"], "-", mejor["info_refaccion"]["precio_estimado_mxn"], "MXN")
else:
    print("No se encontró un diagnóstico sugerido para la entrada proporcionada.")