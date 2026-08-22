from utils.tools_seda import tool_decodificar_vin

def ejecutar_pruebas():
    print("==================================================")
    print("   INICIANDO MÓDULO DE PRUEBAS DE DECODIFICADOR   ")
    print("==================================================\n")

    # -----------------------------------------------------------------
    # TEST 1: Decodificación de VIN
    # -----------------------------------------------------------------
    print("[TEST 1] Decodificando VIN...")
    
    # Caso A: VIN válido (Ejemplo real)
    vin_valido = "Jtlkt324040159970"  # Reemplaza con un VIN válido para tu prueba
    print(f"-> Caso A (VIN válido): {vin_valido}")
    res_vin_valido = tool_decodificar_vin.invoke(vin_valido)
    print(f"{res_vin_valido}\n")

    # Caso B: VIN inválido (Formato incorrecto)
    vin_invalido = "INVALIDVIN12345"
    print(f"-> Caso B (VIN inválido): {vin_invalido}")
    res_vin_invalido = tool_decodificar_vin.invoke(vin_invalido)
    print(f"{res_vin_invalido}\n")

    print("==================================================")
    print("            FIN DE LAS PRUEBAS UNITARIAS          ")
    print("==================================================")

if __name__ == "__main__":
    ejecutar_pruebas()