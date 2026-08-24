import os

# 1. IMPORTACIONES MODULARES
# (Cambia 'ingesta' por el nombre real del archivo .py donde guardaste tu código de ChromaDB)
from ingesta_manuales import procesar_y_guardar_manuales 

# Importamos la tool directamente desde tu archivo de herramientas
from utils.tools_seda import tool_consultar_manuales

def ejecutar_menu_interactive_rag():
    if not os.path.exists("./chroma_db"):
        print("❌ La base de datos vectorial no existe aún. Ejecuta la Opción 1 primero.")
        return

    print("\n✅ Base de datos detectada y Tool cargada. Escribe 'salir' para terminar.")
    
    while True:
        query = input("\n🔎 Ingresa tu consulta de prueba (Ej: 'Diagnóstico Sensor MAP Acura'): ")
        if query.lower() in ['salir', 'exit', 'quit']:
            break
            
        print("\n" + "="*50)
        # Invocamos la tool importada directamente
        respuesta = tool_consultar_manuales.invoke(query)
        print(respuesta)
        print("="*50)

# ==========================================
# MENÚ PRINCIPAL
# ==========================================
if __name__ == "__main__":
    while True:
        print("\n" + "*"*40)
        print("    MENÚ DE TESTING RAG (MODULAR)")
        print("*"*40)
        print("1. Ejecutar Ingesta de PDFs (Llama a procesar_y_guardar_manuales)")
        print("2. Testear Tool de Consultas RAG (Llama a tool_consultar_manuales)")
        print("3. Salir")
        
        opcion = input("\nElige una opción (1/2/3): ")
        
        if opcion == '1':
            print("\n[Sistema] Iniciando pipeline de ingesta...")
            procesar_y_guardar_manuales()
        elif opcion == '2':
            ejecutar_menu_interactive_rag()
        elif opcion == '3':
            print("Saliendo del entorno de pruebas...")
            break
        else:
            print("⚠️ Opción no válida.")