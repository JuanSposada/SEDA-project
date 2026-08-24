import sys
import json
sys.path.append('.')

from utils.seda_engine import execute_diagnostic_pipeline
from utils.tools_seda import tool_decodificar_vin
from utils.llm_manager import get_llm

def collect_vehicle_data() -> dict:
    """
    Recolecta los datos del usuario de forma determinista (guiada)
    para evitar alucinaciones y asegurar contexto limpio.
    """
    print("\n" + "="*50)
    print("SISTEMA SEDA - INGRESO DE DATOS")
    print("="*50)

    has_vin = input("¿Cuentas con el número VIN del vehículo? (S/N): ").strip().upper()

    year, make, model = "", "", ""
    vin_details_json = "No disponible"

    if has_vin == 'S':
        vin = input("Ingresa los 17 caracteres del VIN: ").strip().upper()
        print("[Sistema] Decodificando VIN, por favor espera...")

        vin_response = tool_decodificar_vin.invoke(vin)

        if isinstance(vin_response, dict) and "error" not in vin_response:
            make = vin_response.get("make", "")
            model = vin_response.get("model", "")
            year = str(vin_response.get("year", ""))

            raw_details = vin_response.get("details", {})
            vin_details_json = json.dumps(raw_details, indent=2, ensure_ascii=False)
        
            print(f"\nVIN detectado exitosamente ({vin_response.get('estatus', 'OK')})")
            if make or model or year:
                print(f"-> Vehículo detectado: {year} {make} {model}".strip())
        else:
            err_msg = vin_response.get("error") if isinstance(vin_response, dict) else vin_response
            print(f"⚠️ {err_msg}")

    # Se piden los datos del vehículo que hayan quedado vacíos (o si no se proporcionó VIN)
    if not (year and make and model):
        print("\nPor favor, confirma o completa los datos del vehículo:")    
        if not year: year = input("Ingresa el Año del vehículo: ").strip()
        if not make: make = input("Ingresa la Marca del vehículo: ").strip()
        if not model: model = input("Ingresa el Modelo del vehículo: ").strip()
        
    has_dtc = input("\n¿Cuentas con el código DTC (Código de Falla)? (S/N): ").strip().upper()

    dtc_code = ""
    sintomas_user = ""

    if has_dtc == 'S':
        dtc_code = input("\nIngresa el Código de Falla (Ej. P1106): ").strip().upper()
    else: 
        sintomas_user = input("Describe los síntomas del auto (Ej. tiembla mucho y tira humo negro): ").strip()

    return {
        "year": year,
        "make": make,
        "model": model,
        "dtc_code": dtc_code,
        "sintomas": sintomas_user,
        "vin_details": vin_details_json
    }

def run_seda_pipeline(llm, vehicle_data: dict):
    """
    Ejecuta el pipeline de RAG, bases de datos y herramientas a través del motor SEDA.
    """
    res = execute_diagnostic_pipeline(vehicle_data, llm=llm)
    if res.get("error"):
        print(f"⚠️ Alerta: {res['error']}")
    return res.get("reporte_final", "")


if __name__ == "__main__":
    llm = get_llm()
    if not llm:
        print("Error: No se pudo inicializar el modelo de lenguaje. Verifica la configuración.")
        sys.exit(1)

    v_data = collect_vehicle_data()

    try:
        report = run_seda_pipeline(llm, v_data)
        print("\n" + "="*50)
        print("                 REPORTE DIAGNOSTICO SEDA                  ")
        print("="*50)
        print(report)
        print("="*50)
    
    except Exception as e:
        print(f"\n❌ Error durante el pipeline: {str(e)}")