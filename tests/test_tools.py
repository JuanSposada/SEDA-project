import sys
# Aseguramos que Python encuentre las herramientas si están en el mismo directorio
sys.path.append('.') 

from utils.tools_seda import tool_consulta_db_dtc, tool_busqueda_rockauto

def ejecutar_pruebas():
    print("==================================================")
    print("   INICIANDO MÓDULO DE PRUEBAS DE HERRAMIENTAS   ")
    print("==================================================\n")

    # -----------------------------------------------------------------
    # TEST 1: Tu herramienta de Base de Datos Relacional (SQLite)
    # -----------------------------------------------------------------
    print("[TEST 1] Consultando tu Base de Datos 'dtc_codes.db'...")
    
    # Caso A: Código específico de Fabricante (Usa tu dato real del repo)
    print("-> Caso A (Código específico con marca):")
    res_especifico = tool_consulta_db_dtc.invoke("P1106, Acura")
    print(f"{res_especifico}\n")

    # Caso B: Código genérico (Debería entrar por el fallback si no coincide la marca)
    print("-> Caso B (Código genérico con marca aleatoria):")
    res_generico = tool_consulta_db_dtc.invoke("P0301, Toyota")
    print(f"{res_generico}\n")

    # -----------------------------------------------------------------
    # TEST 2: Cliente de RockAuto API (Prueba de Red e Integración)
    # -----------------------------------------------------------------
    print("[TEST 2] Consultando catálogo dinámico de RockAuto...")
    # Formato obligatorio: Marca, Año, Modelo, Categoría
    entrada_ra = "Scion, 2004, xB, Ignition"
    print(f"-> Petición externa para: '{entrada_ra}'")
    
    try:
        res_rockauto = tool_busqueda_rockauto.invoke(entrada_ra)
        print(f"{res_rockauto}\n")
    except Exception as e:
        print(f"❌ Error en conexión a RockAuto: {str(e)}\n")

    print("==================================================")
    print("            FIN DE LAS PRUEBAS UNITARIAS          ")
    print("==================================================")

if __name__ == "__main__":
    ejecutar_pruebas()