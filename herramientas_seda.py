import sqlite3
from langchain.tools import tool
from rockauto_api import RockAutoClient # Cleinte de la librería rsp2k/rockauto-api
import asyncio

"""
TOOL # 1 Herramienta para consulta en base de datos local de dtc_codes.db
"""
@tool
def tool_consulta_db_dtc(codigo_y_marca: str) -> str:
    """
    Busca la definicon e interpretacion tecnica exacta de codigo de falla OBD-II
    Entrada: coigo estandar de 5 caracteres"""
    partes = [p.strip() for p in codigo_y_marca.split(",")]
    codigo_limpio = partes[0].upper()
    marca_limpio = partes[1].upper()
    try:
        conn = sqlite3.connect('data/dtc_codes.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT code, manufacturer, description, type FROM dtc_definitions WHERE code = ? and manufacturer = ? LIMIT 1",
            (codigo_limpio, marca_limpio)
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
            return f"[Resultado DB local] el codigo {codigo_limpio} no se encontro en el catalogo de definiciones existente"
        
    except Exception as e:
        return f"Error al consultar la base de datos relacional: {str(e)}"


async def _ejecutar_busqueda_rockauto_async(make: str, year: int, model: str, category: str) -> str:
    """Funcion para navegar en el arbol de busqueda de RockAuto"""
    async with RockAutoClient() as client:
        try:
            vehicle = await client.get_vehicle(make=make.upper(), year=int(year), model=model.upper())
        
        except Exception:
            return f"[RockAuto] Error: No se localizo el vehiculo {year} {make} {model}"

        # Consultar autopartes
        try:
            await asyncio.sleep(0.5)
            parts_result = await vehicle.get_parts_by_category(category)
            if not parts_result or parts_result.count == 0:
                return f"[RockAuto] Vehiculo encontrado, pero no hay piezas bajo la categoria '{category}'.\n"
            
            # Formatear la salida 
            salida = f"[RockAuto API] Componente para {year} {make} {model} -> Categoria: '{category}'\n"

            lista_partes = list(parts_result.parts)
            for part in lista_partes:
                nombre_pieza = getattr(part, 'name', 'Componente')
                url_catalogo = getattr(part, 'url', 'N/A')
                salida += f"- {nombre_pieza}:\n Enlace al catalogo: {url_catalogo}\n\n"
            return salida
            # salida = f"[RockAuto API] Diagnóstico de atributos para la pieza:\n"
            # if parts_result.parts:
            #     ejemplo_pieza = parts_result.parts[:3]
            #     # Esto listará en tu test todos los campos reales que contiene el objeto PartInfo
            #     salida += f"Campos disponibles: {list(ejemplo_pieza.__dict__.keys())}\n"
            #     salida += f"Contenido completo: {str(ejemplo_pieza)}\n"
            # return salida
        
        except Exception as e:
            return f"[RockAuto] error al extraer partes de la categoria '{category}: {str(e)}"
"""
TOOL # 2 Busqueda de refacciones utilizando la rockauto-api
"""
@tool
def tool_busqueda_rockauto(datos_vehiculo_y_categoria: str) -> str:
    """
    Busca componentes y precios reales en RockAuto.com navegando su API interna.
    Entrada esperada: Una cadena exacta con 'Marca, Año, Modelo, Categoría' 
    (ej. 'Toyota, 2020, Camry, Brake & Wheel Hub' o 'Scion, 2004, xB, Ignition').
    """
    partes = [p.strip() for p in datos_vehiculo_y_categoria.split(",")]
    if len(partes) < 4:
        return "Error: Formato requerido para RockAuto: Marca, Año, Modelo, Categoría'"
    
    make, year, model, category = partes[0], partes[1], partes[2], partes[3]

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_ejecutar_busqueda_rockauto_async(make, year, model, category))