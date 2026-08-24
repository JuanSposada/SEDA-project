import sqlite3
import re
import asyncio
import requests
from langchain.tools import tool
from rockauto_api import RockAutoClient
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from utils.make_manager import get_make_for_search, get_all_related_makes

try:
    from vininfo import Vin
    HAS_VININFO = True
except ImportError:
    HAS_VININFO = False

STOPWORDS_ES = {"el", "la", "los", "las", "un", "una", "unos", 
                "unas", "y", "o", "de", "del", "a", "al", "con", 
                "en", "por", "para", "mi", "se", "que", "es", "no", 
                "si", "me", "mucho", "muy"} 
"""
TOOL # 1 Herramienta para consulta en base de datos local de dtc_codes.db
"""
_VECTOR_STORE = None

def _get_vector_store():
    global _VECTOR_STORE
    if _VECTOR_STORE is None:
        print("[Sistema] Inicializando modelo de Embeddings para Manuales Locales (Singleton)...")
        modelo_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        _VECTOR_STORE = Chroma(persist_directory="./chroma_db", embedding_function=modelo_embeddings)
    return _VECTOR_STORE


def _run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


@tool
def tool_consulta_db_dtc(codigo: str, marca: str) -> str:
    """
    Busca la definición e interpretación técnica exacta de un código de falla OBD-II (DTC) en la base de datos local.
    
    Parámetros:
      - codigo: El código de falla estándar de 5 caracteres (ej. 'P1106', 'P0300').
      - marca: La marca del vehículo (ej. 'Acura', 'Honda', 'Toyota'). Solo el nombre del fabricante.
    """
    marca_limpia = marca.strip().split()[0].upper() if marca else ""
    codigo_limpio = codigo.strip().upper()
    try:
        with sqlite3.connect('data/dtc_codes.db') as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT manufacturer FROM dtc_definitions")
            marcas_db = [row[0].upper() for row in cursor.fetchall()]

            target_make = get_make_for_search(marca_limpia, marcas_db)

            cursor.execute(
                "SELECT code, manufacturer, description, type FROM dtc_definitions WHERE code = ? and manufacturer = ? LIMIT 1",
                (codigo_limpio, target_make.upper())
            )
            resultado = cursor.fetchone()
            
            if not resultado:
                cursor.execute(
                    "SELECT code, manufacturer, description, type FROM dtc_definitions WHERE code = ? LIMIT 1",
                    (codigo_limpio,)
                )
                resultado = cursor.fetchone()
        
        if resultado:
            code, fabricante, descripcion, tipo = resultado
            return (f"-- Resultado DB Local --\n"
                    f"Code: {code}\n"
                    f"Make: {fabricante}\n"
                    f"Description: {descripcion}\n"
                    f"System Type: {tipo}"
                    )
        else:
            return f"[Resultado DB local] el codigo {codigo} no se encontro en el catalogo de definiciones existente"
        
    except Exception as e:
        return f"Error al consultar la base de datos relacional: {str(e)}"


# Diccionario extendido de sinónimos automotrices obtenido de la DB dtc_codes.db
SINONIMOS_AUTOMOTRICES = {
    # Sensores de Presión y Emisiones (Exhaust & Emission)
    "baro": ["map", "manifold pressure", "barometric", "baro"],
    "barometric": ["map", "manifold pressure", "baro", "barometric"],
    "map": ["map", "manifold pressure", "baro"],
    "egr": ["egr", "exhaust gas recirculation", "egr valve", "egr gasket"],
    "evap": ["evap", "vapor canister", "purge valve", "vent valve", "evaporative"],
    "o2": ["o2", "oxygen", "oxigeno", "ho2s", "lambda"],
    "ho2s": ["o2", "oxygen", "ho2s", "lambda"],
    "knock": ["knock", "detonation", "detonacion"],
    "catalyst": ["catalytic", "converter", "catalizador"],
    "catalytic": ["catalytic", "converter"],
    "air injection": ["air injection", "secondary air"],

    # Admisión y Aire (Fuel & Air)
    "maf": ["maf", "mass air flow", "air flow", "flujo de aire"],
    "iat": ["intake air temperature", "charge temperature", "iat"],
    "tp": ["throttle position", "tps", "throttle body"],
    "tps": ["throttle position", "tps", "throttle body"],
    "app": ["accelerator pedal", "pedal position"],
    "iac": ["idle air control", "iac", "idle speed"],
    "injector": ["fuel injector", "inyector"],
    "fuel pump": ["fuel pump", "bomba de combustible"],

    # Encendido y Tiempo (Ignition)
    "ckp": ["crankshaft", "crank", "posicion del cigueñal"],
    "cmp": ["camshaft", "cam", "posicion del arbol de levas"],
    "crankshaft": ["crankshaft", "ckp"],
    "camshaft": ["camshaft", "cmp"],
    "spark": ["spark plug", "bujia", "ignition coil", "bobina"],
    "ignition": ["ignition coil", "bobina", "spark plug"],

    # Enfriamiento y Calefacción (Cooling & Heating)
    "ect": ["coolant temperature", "temperature sender", "sensor de temperatura"],
    "coolant": ["coolant temperature", "thermostat", "radiator", "water pump"],
    "thermostat": ["thermostat", "termostato"],

    # Frenos y Tracción (Brake & Wheel Hub)
    "abs": ["abs wheel speed", "wheel speed sensor", "speed sensor", "abs hydraulic"],
    "brake": ["brake pad", "brake rotor", "caliper", "brake booster"],
    "bbv": ["brake booster vacuum", "vacuum sensor"],

    # Transmisión (Transmission-Automatic / Manual)
    "tcc": ["torque converter", "solenoid"],
    "tfp": ["fluid pressure", "transmission fluid"],
    "tcm": ["transmission control", "tcm"],
    "speed sensor": ["speed sensor", "output speed", "input speed", "vss"],
    "vss": ["speed sensor", "vehicle speed"],

    # Dirección y Suspensión (Steering / Suspension)
    "steering": ["power steering", "steering pressure", "rack and pinion"],
    "suspension": ["strut", "shock absorber", "control arm", "ball joint"],
    "tpms": ["tire pressure", "tpms"]
}


async def _ejecutar_busqueda_rockauto_async(make: str, year: int, model: str, pieza_en_ingles: str) -> str:
    """Funcion para navegar en el arbol de busqueda de RockAuto con sinónimos automotrices"""
    async with RockAutoClient() as client:
        vehicle = None
        for intento in range(3):
            try:
                vehicle = await client.get_vehicle(make=make.upper(), year=int(year), model=model.upper())
                if vehicle:
                    break
            except Exception:
                await asyncio.sleep(0.5)

        if not vehicle:
            return f"[RockAuto] Error: No se localizó el vehículo {year} {make} {model} tras varios intentos de conexión."

        # Todas las 11 categorías clave requeridas de RockAuto
        categorias_clave = [
            "Fuel & Air", 
            "Exhaust & Emission", 
            "Electrical", 
            "Ignition", 
            "Engine",
            "Cooling & Heating",
            "Transmission-Automatic",
            "Transmission-Manual",
            "Brake & Wheel Hub",
            "Steering",
            "Suspension"
        ]

        busqueda_clean = pieza_en_ingles.lower().strip()
        
        # Términos ampliados con diccionario de sinónimos automotrices
        terminos_busqueda = [busqueda_clean]
        for clave, sinons in SINONIMOS_AUTOMOTRICES.items():
            if clave in busqueda_clean:
                terminos_busqueda.extend(sinons)
        terminos_busqueda = list(set(terminos_busqueda))

        piezas_encontradas = []
        todas_las_piezas = []

        for category in categorias_clave:
            try:
                await asyncio.sleep(0.3)
                parts_result = await vehicle.get_parts_by_category(category)
                if parts_result and parts_result.parts:
                    for part in list(parts_result.parts):
                        nombre_pieza = getattr(part, 'name', '')
                        url_catalogo = getattr(part, 'url', 'N/A')
                        if url_catalogo and url_catalogo.startswith("/"):
                            url_catalogo = f"https://www.rockauto.com{url_catalogo}"

                        todas_las_piezas.append(f"- {nombre_pieza} ({category})")

                        # Coincidencia semántica flexible por término o sinónimos
                        if any(term in nombre_pieza.lower() for term in terminos_busqueda):
                            piezas_encontradas.append(f"- {nombre_pieza} (Categoría: {category}):\n  Enlace: {url_catalogo}\n")
            except Exception:
                continue   

        if piezas_encontradas:
            salida = f"[RockAuto API] Refacciones encontradas para '{pieza_en_ingles}':\n\n"
            salida += "\n".join(piezas_encontradas[:5])
            return salida

        # Fallback informativo si no hay coincidencia directa
        salida_fallback = (
            f"[RockAuto] El vehículo {year} {make} {model} fue localizado, pero no hay refacción nombrada exactamente '{pieza_en_ingles}'.\n"
            f"Sugerencia de catálogo: En esta marca, el componente equivalente suele registrarse bajo alguna de estas refacciones disponibles:\n"
        )
        salida_fallback += "\n".join(todas_las_piezas[:5])
        return salida_fallback

"""
TOOL # 2 Busqueda de refacciones utilizando la rockauto-api
"""
@tool
def tool_busqueda_rockauto(datos_vehiculo_y_pieza: str) -> str:
    """
    Busca componentes reales en RockAuto navegando su API oficial.
    Entrada esperada: Una cadena exacta con 'Marca, Año, Modelo, Nombre de la Pieza en Inglés' 
    (ej. 'Acura, 2000, TL, MAP Sensor' o 'Toyota, 2010, Camry, CKP').
    """
    partes = [p.strip() for p in datos_vehiculo_y_pieza.split(",")]
    if len(partes) < 4:
        return "Error: Formato requerido para RockAuto: 'Marca, Año, Modelo, Pieza'"
    
    make = partes[0]
    year = partes[1]
    model = partes[2]
    pieza = ", ".join(partes[3:]) if len(partes) > 4 else partes[3]

    try:
        return _run_async(_ejecutar_busqueda_rockauto_async(make, int(year), model, pieza))
    except Exception as e:
        return f"[RockAuto Error]: {str(e)}"


@tool
def tool_decodificar_vin(vin: str) -> str:
    """
    Decodifica un VIN (Vehicle Identification Number) para obtener información del vehículo.
    Entrada esperada: VIN de 17 caracteres (ej. '1HGCM82633A123456').
    """
    vin_limpio = vin.strip().upper()
    if len(vin_limpio) != 17:
        return f"Error: {vin_limpio} El VIN debe tener exactamente 17 caracteres."

    url_api = f"https://vpic.nhtsa.dot.gov/api/vehicles/decodevin/{vin_limpio}?format=json"

    try:
        response = requests.get(url_api, timeout=5)
        response.raise_for_status()
        data = response.json()
        results = data.get("Results", [])
        
        if results:
            info_bruta = {item["Variable"]: item["Value"] for item in results if item["Value"]}
            return {
                "status": "online",
                "make": info_bruta.get("Make", ""),
                "model": info_bruta.get("Model", ""),
                "year": info_bruta.get("Model Year", ""),
                "details": info_bruta
            }
    
    except requests.exceptions.RequestException as e:
        print(f"[Aviso] Sin conexión a internet para VIN. Intentando modo offline...")

    if HAS_VININFO:
        try:
            v = Vin(vin_limpio)
            years = v.years if v.years else [""]
            calc_year = years[-1] if isinstance(years, list) else years
            return {
                "status": "offline",
                "make": v.manufacturer or v.brand or "",
                "model": "",
                "year": str(calc_year),
                "details": {
                    "country": v.country,
                    "region": v.region,
                    "WMI": v.wmi,
                }
            }
            
        except Exception as e:
            return f"Error: No se pudo decodificar el VIN {vin_limpio} ni con la API ni con vininfo. Detalles: {str(e)}"
    return {"error": "Sin conexión a internet y librería vininfo no disponible."}


@tool
def tool_buscar_refaccion_web(datos_vehiculo_y_pieza: str) -> str:
    """
    Busca en internet opciones de compra, precios y enlaces para una refacción automotriz.
    Entrada esperada: 'Año Marca Modelo Nombre de la Pieza' (ej. '2000 Acura TL MAP Sensor').
    """
    query_limpia = datos_vehiculo_y_pieza.replace(",", " ").strip()
    query_busqueda = f"buy {query_limpia} autoparts price"

    try:
        print(f"[Buscador Web] Buscando: {query_busqueda}...")
        buscador = DuckDuckGoSearchResults(num_results=5)
        resultados_raw = buscador.invoke(query_busqueda)

        if not resultados_raw:
            return f"No se encontraron resultados en la web para '{query_busqueda}'."

        # Parsear la cadena de DuckDuckGo en elementos estructurados con Regex
        pattern = r'snippet:\s*(.*?),\s*title:\s*(.*?),\s*link:\s*(https?://[^\s,\]]+)'
        coincidencias = re.findall(pattern, str(resultados_raw), re.DOTALL)

        if not coincidencias:
            return str(resultados_raw)

        salida_formateada = "### 🌐 Refacciones y Tiendas Encontradas en la Web:\n\n"
        for i, (snippet, title, link) in enumerate(coincidencias, 1):
            title_clean = title.strip()
            snippet_clean = snippet.strip().replace("\n", " ")
            link_clean = link.strip()

            salida_formateada += (
                f"{i}. 🛒 **[{title_clean}]({link_clean})**\n"
                f"   - 📝 **Detalle:** {snippet_clean}\n"
                f"   - 🔗 **Enlace Directo:** [{link_clean}]({link_clean})\n\n"
            )

        return salida_formateada.strip()

    except Exception as e:
        return f"[Buscador Web] Error al realizar la búsqueda: {str(e)}"


@tool
def tool_consultar_manuales(query: str) -> str:
    """
    Busca información técnica, de diagnóstico, procedimientos o voltajes en los manuales de taller locales (PDFs).
    Entrada esperada: Una consulta muy específica con la marca, modelo, y el componente o código.
    Ejemplo: 'Acura TL 2000 diagnóstico Sensor MAP P1106 voltajes'
    """
    print(f"\n[RAG] Buscando en los manuales locales para la consulta: '{query}'...")

    try:
        vector_store = _get_vector_store()
        resultados = vector_store.similarity_search(query, k=10)

        if not resultados:
            return f"[RAG] No se encontraron fragmentos relevantes en los manuales locales para la consulta: '{query}'."

        texto_recuperado = "[EXTRACTO DE MANUALES LOCALES]\n\n"

        for i, doc in enumerate(resultados):
            fuente = doc.metadata.get("source", " Manual Desconocido")
            pagina = doc.metadata.get("page", "Página Desconocida")
            nombre_archivo = fuente.split("/")[-1].split("\\")[-1]

            texto_recuperado += f"--- Extracto {i+1} (Fuente: {nombre_archivo}, página: {pagina}) ---\n"
            texto_recuperado += f"{doc.page_content}\n\n"

        return texto_recuperado

    except Exception as e:
        return f"[RAG] Error al buscar en los manuales locales: {str(e)}"


@tool
def tool_buscar_por_sintomas(sintomas: str, marca: str = "") -> dict:
    """
    Busca códigos de falla DTC probables en la base de datos basándose en síntomas.
    """
    clean_brand = marca.strip().upper() if marca else ""
    marcas_relevantes = get_all_related_makes(marca)

    palabras = re.findall(r'\b\w+\b', sintomas.lower())
    palabras_clave = [p for p in palabras if p not in STOPWORDS_ES and len(p) > 2]
    
    if not palabras_clave:
        return {"error": "No se identificaron palabras clave suficientes en los síntomas."}

    fts_query = " OR ".join(palabras_clave)

    try:
        with sqlite3.connect('data/seda_diagnostico.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            sql = """
                SELECT codigo, significado, marcas_afectadas, sintomas, causas, soluciones, 
                       codigos_relacionados, puedo_manejarlo, reparacion, ubicacion, diagnostico, errores_comunes
                FROM busqueda_global
                WHERE busqueda_global MATCH ?
                LIMIT 15
            """
            cursor.execute(sql, (fts_query,))
            filas = cursor.fetchall()

        if not filas:
            return {"error": f"No se encontraron códigos coincidentes con los síntomas: '{sintomas}'."}

        coincidencias_exactas_p = []
        coincidencias_exactas_otras = []
        coincidencias_generales_p = []
        coincidencias_generales_otras = []

        for f in filas:
            item = dict(f)
            code = str(item.get("codigo", "")).strip().upper()
            marcas_texto = str(item.get("marcas_afectadas", "")).upper()
            
            match_marca = any(m in marcas_texto for m in marcas_relevantes) if marcas_relevantes else False
            is_p_code = code.startswith("P")

            item["coincide_marca"] = match_marca

            if match_marca and is_p_code:
                coincidencias_exactas_p.append(item)
            elif match_marca:
                coincidencias_exactas_otras.append(item)
            elif is_p_code:
                coincidencias_generales_p.append(item)
            else:
                coincidencias_generales_otras.append(item)

        resultados = (
            coincidencias_exactas_p +
            coincidencias_exactas_otras +
            coincidencias_generales_p +
            coincidencias_generales_otras
        )

        return {
            "codigos_probables": resultados[:3],
            "total_encontrados": len(resultados)
        }


    except Exception as e:
        return {"error": f"Error al ejecutar la búsqueda por síntomas en FTS5: {str(e)}"}


@tool
def tool_consulta_dtc_enriquecida(codigo: str) -> dict:
    """Extrae contexto experto (síntomas, causas, soluciones) de obd_informacion."""
    clean_code = codigo.strip().upper()
    try:
        with sqlite3.connect('data/seda_diagnostico.db') as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = """
                SELECT codigo, significado, marcas_afectadas, sintomas, causas, 
                       soluciones, codigos_relacionados, puedo_manejarlo, 
                       reparacion, ubicacion, diagnostico, errores_comunes
                FROM obd_informacion
                WHERE codigo = ? LIMIT 1
            """
            cursor.execute(query, (clean_code,))
            row = cursor.fetchone()

        return dict(row) if row else {"error": f"No hay contexto enriquecido para '{clean_code}'."}
    except Exception as e:
        return {"error": f"Error BD Enriquecida: {str(e)}"}

        