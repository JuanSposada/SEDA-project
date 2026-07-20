import sys
sys.path.append('.')

from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from herramientas_seda import tool_busqueda_rockauto, tool_consulta_db_dtc

def inicializar_agente_seda():
    print("[CONFIG] Cargando herramientas y modelo local (Ollama)")

    # Difiniendo el modelo local
    llm = ChatOllama(model="qwen2.5", temperature=0.1).bind_tools([
        tool_consulta_db_dtc, 
        tool_busqueda_rockauto
    ])

    return llm

def ejecutar_agente(llm, consulta_usuario):

    tools = {
        "tool_consulta_db_dtc": tool_consulta_db_dtc,
        "tool_busqueda_rockauto": tool_busqueda_rockauto
    }
    print(f"\n[PENSANDO] Evaluando herramientas para la consulta...")
    respuesta_llm = llm.invoke(consulta_usuario)

    if respuesta_llm.tool_calls:
        print(f"[ACCION] El modelo decidió usar herramientas.")
        resultados_contexto = []

        for call in respuesta_llm.tool_calls:
            nombre_tool = call["name"]
            argumentos = call["args"]

            if nombre_tool in tools:
                print(f" -> Ejecutando {nombre_tool} con argumentos: {argumentos}")

                if nombre_tool == "tool_consulta_db_dtc":
                    valor_arg = list(argumentos.values())[0] if argumentos else "P1106, Acura"
                    if "," not in str(valor_arg):
                        valor_arg = f"{valor_arg}, Acura"
                    res_tool = tools[nombre_tool].invoke(valor_arg)

                elif nombre_tool == "tool_busqueda_rockauto":
                    try:
                        res_tool = tools[nombre_tool].invoke(argumentos)
                    except:
                        valor_arg = ", ".join([str(v) for v in argumentos.values()])
                        res_tool = tools[nombre_tool].invoke(valor_arg)

                else:
                    res_tool = tools[nombre_tool].invoke(argumentos)
                
                resultados_contexto.append(f"Resultado de {nombre_tool}: {res_tool}")

        # Inferencia final con el contexto recolectado
        prompt_final = f"""
        Eres SEDA (Sistema Experto de Diagnóstico Automotriz). Responde al usuario en español basándote estrictamente en los siguientes datos obtenidos del sistema:
        
        Datos obtenidos:
        {chr(10).join(resultados_contexto)}
        
        Consulta original del usuario:
        {consulta_usuario}
        """
        print(f"[PROCESANDO] Generando diagnóstico final...")

        diagnostico = ChatOllama(model="qwen2.5", temperature=0.1).invoke(prompt_final)
        return diagnostico.content
    else:
        return respuesta_llm.content


if __name__ == "__main__":
    agente = inicializar_agente_seda()

    print("\n==================================================")
    consulta = (
        "Tengo un auto Acura con el código de falla P1106. "
        "¿Qué significa y qué componentes puedo revisar en un Scion xB 2004 en la categoría de Ignition?"
    )
    print(f" Lanzando consulta de pruena: \n'{consulta}")
    print("==================================================\n")

    try:
        respuesta = ejecutar_agente(agente, consulta)
        print("\n==================================================")
        print("                 RESPUESTA FINAL                  ")
        print("==================================================")
        print(respuesta)
    
    except Exception as e:
        print(f"\nError durante la ejecucion del Agente: {str(e)}")