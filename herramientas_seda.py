import sqlite3
import asyncio
import requests
from langchain.tools import tool
from vininfo import Vin
from rockauto_api import RockAutoClient
from langchain_community.tools import DuckDuckGoSearchResults

"""
TOOL # 1 Herramienta para consulta en base de datos local de dtc_codes.db
"""
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
        conn = sqlite3.connect('data/dtc_codes.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT code, manufacturer, description, type FROM dtc_definitions WHERE code = ? and manufacturer = ? LIMIT 1",
            (codigo_limpio, marca_limpia)
        )
        resultado = cursor.fetchone()
        
        if not resultado:
            cursor.execute(
                "SELECT code, manufacturer, description, type FROM dtc_definitions WHERE code = ? LIMIT 1",
                (codigo_limpio,)
            )
            resultado = cursor.fetchone()
        conn.close()
        
        if resultado:
            code, fabricante, descripcion, tipo = resultado
            return (f"-- Resultado DB Local --\n"
                    f"Codigo: {code}\n"
                    f"Fabricante: {fabricante}\n"
                    f"Descripcion {descripcion}\n"
                    f"Tipo de Sistema {tipo}"
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
    
    make, year, model, pieza = partes[0], partes[1], partes[2], partes[3]

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_ejecutar_busqueda_rockauto_async(make, year, model, pieza))


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
        if response.status_code != 200:
            return f"Error: No se pudo conectar a la API de decodificación de VIN. Código HTTP: {response.status_code}"
        data = response.json()
        resultados = data.get("Results", [])
        if not resultados:
            return f"Error: No se encontraron resultados para el VIN {vin_limpio}."
        
        info_vehiculo = {item["Variable"]: item["Value"] for item in resultados if item["Value"]}
        return f"[Decodificación VIN] Información extraída:\n" + "\n".join(f"{k}: {v}" for k, v in info_vehiculo.items())
    
    except requests.exceptions.RequestException as error_red:
        print(f"Error al decodificar el VIN: {str(error_red)} intentando modo offline con vininfo...")

        try:
            v = Vin(vin_limpio)
            info_vehiculo = {
                "assembler": v.assembler,
                "brand": v.brand,
                "country": v.country,
                "model_year": v.years,
                "region": v.region,
                "details": v.details,
            }
        except Exception as e:
            return f"Error: No se pudo decodificar el VIN {vin_limpio} ni con la API ni con vininfo. Detalles: {str(e)}"


@tool
def tool_buscar_refaccion_web(datos_vehiculo_y_pieza: str) -> str:
    """
    Busca en internet opciones de compra, precios y enlaces para una refacción automotriz.
    Entrada esperada: 'Año Marca Modelo Nombre de la Pieza' (ej. '2000 Acura TL MAP Sensor').
    """

    #Limpuar el input por si el LLM pone comas
    query_limpia = datos_vehiculo_y_pieza.replace(",", " ").strip()

    # Armado de query enfocado en compras
    query_busqueda = f"buy {query_limpia} autoparts price"

    buscador = DuckDuckGoSearchResults(num_results=5)

    try:
        print(f"[Buscador Web] Buscando: {query_busqueda}...")
        resultados = buscador.invoke(query_busqueda)

        if not resultados:
            return f"[Buscador Web] No se encontraron resultados para '{query_busqueda}'."

        return f"Resultados encontrados en la web (usa esta información para recomendarle al usuario dónde comprar):\n{resultados}"

    except Exception as e:
        return f"[Buscador Web] Error al realizar la búsqueda: {str(e)}"