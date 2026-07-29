#@tool
# def tool_busqueda_rockauto(datos_vehiculo_y_pieza: str) -> str:
#     """
#     Busca la refacción exacta en la API interna de RockAuto.
#     Entrada: 'Marca, Año, Modelo, Nombre de la Pieza' (ej. 'Acura, 2000, TL, MAP Sensor').
#     """
    
#     search_query = datos_vehiculo_y_pieza.replace(",", " ") if ',' in datos_vehiculo_y_pieza else datos_vehiculo_y_pieza
#     url_api = "https://www.rockauto.com/catalog/searchapi.php"
#     payload = {
#         "is_search": 1,
#         "tab": "catalog",
#         "text": search_query
#     }

#     try:
#         # Añadimos un encabezado de User-Agent para evitar bloqueos
#         headers = {
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
#         }
#         response = requests.post(url_api,data=payload, headers=headers)
#         data = response.json()

#         if "search_api_results" in data and "Suggestions" in data["search_api_results"]:
#             sugerencias = data["search_api_results"]["Suggestions"]

#             for item in sugerencias:
#                 if item.get("Type") == "Car":
#                     make = item.get("Make","")
#                     year = item.get("Year", "")
#                     model = item.get("Model","")
#                     engine = item.get("Engine", "").replace(" ", "+")
#                     car_code = item.get("CarCode","")
#                     group_name = item.get("GroupName", "").replace(" ", "+")
#                     part_type_description = item.get("PartTypeDesc", "").replace(" ", "+")
#                     part_type = item.get("PartType", "")

#             url_exacto = f"https://www.rockauto.com/en/catalog/{make},{year},{model},{engine},{car_code},{group_name},{part_type_description},{part_type}"

#             return (f"Refacción encontrada en el catálogo: {item.get('PartTypeDesc', '').title()}\n"
#                             f"Enlace directo para compra: {url_exacto}")
        
#         return f"RockAuto no arrojó resultados específicos para la pieza '{datos_vehiculo_y_pieza}' en el vehículo indicado."

#     except Exception as e:
#         return f"Error de conexión con RockAuto: {str(e)}"
import requests
import json

def test_busqueda_con_sesion(query: str):
    print(f"\n[!] Iniciando búsqueda inteligente para: '{query}'")
    
    # 1. CREAMOS UNA SESIÓN PERSISTENTE (Igual que hace tu librería de GitHub)
    session = requests.Session()
    
    # 2. Configuramos las cabeceras base simulando un navegador Chrome
    headers_base = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        "Connection": "keep-alive"
    }
    session.headers.update(headers_base)
    
    try:
        # 3. EL TRUCO MAESTRO: Visitamos la página principal PRIMERO.
        # Esto hace que RockAuto nos asigne una Cookie válida y nos deje pasar.
        print(" -> Paso 1: Entrando a RockAuto para obtener Cookies de sesión...")
        home_response = session.get("https://www.rockauto.com/", timeout=10)
        
        # Validamos que nos hayan dado la cookie principal
        cookies_guardadas = session.cookies.get_dict()
        print(f" -> Cookies obtenidas: {list(cookies_guardadas.keys())}")
        
        # 4. Actualizamos las cabeceras específicamente para la petición AJAX (API)
        session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://www.rockauto.com",
            "Referer": "https://www.rockauto.com/"
        })
        
        payload = {
            "is_search": 1,
            "tab": "catalog",
            "text": query
        }
        
        # 5. Disparamos a la API usando la MISMA sesión (llevando las cookies automáticamente)
        print(" -> Paso 2: Enviando payload a la API de búsqueda (searchapi.php)...")
        url_api = "https://www.rockauto.com/catalog/searchapi.php"
        api_response = session.post(url_api, data=payload, timeout=10)
        
        if api_response.status_code != 200:
            return f"❌ Fallo en el servidor: {api_response.status_code}"
            
        # Intentamos parsear el JSON
        data = api_response.json()
        
        # 6. Procesamos los resultados de RockAuto
        if "search_api_results" in data and "Suggestions" in data["search_api_results"]:
            sugerencias = data["search_api_results"]["Suggestions"]
            
            for item in sugerencias:
                if item.get("Type") == "Car":
                    make = item.get("Make", "").strip().lower()
                    year = item.get("Year", "").strip()
                    model = item.get("Model", "").strip().lower()
                    engine = item.get("Engine", "").strip().replace(" ", "+")
                    car_code = item.get("CarCode", "").strip()
                    group_name = item.get("GroupName", "").strip().replace(" ", "+").replace("&", "%26")
                    part_type_desc = item.get("PartTypeDesc", "").strip().replace(" ", "+")
                    part_type = item.get("PartType", "").strip()
                    
                    url_exacto = f"https://www.rockauto.com/en/catalog/{make},{year},{model},{engine},{car_code},{group_name},{part_type_desc},{part_type}"
                    nombre_pieza = item.get("PartTypeDesc", "").title()
                    
                    return f"✅ ¡ÉXITO!\nPieza encontrada: {nombre_pieza}\nEnlace Real: {url_exacto}"
                    
        return "⚠️ RockAuto procesó la petición, pero no encontró esa pieza."

    except json.decoder.JSONDecodeError:
        return "❌ Error: RockAuto devolvió HTML en blanco o captcha (Aún nos bloquea)."
    except Exception as e:
        return f"❌ Error general: {str(e)}"

if __name__ == "__main__":
    resultado = test_busqueda_con_sesion("acura 2000 tl MAP sensor")
    print("\n" + "="*50)
    print(resultado)
    print("="*50)