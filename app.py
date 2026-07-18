import streamlit as st
# Importamos las funciones lógicas de tu script anterior
from huggin_hibrido import cargar_base_conocimiento, recuperar_contexto_semantico, generar_respuesta_sistema_experto

# Configuración de la página web
st.set_page_config(page_title="SEDA - Sistema Experto", page_icon="🚗", layout="centered")

# Encabezado principal
st.title("🚗 SEDA")
st.subheader("Sistema Experto de Diagnóstico Automotriz")
st.write("Prototipo de Inteligencia Artificial para asistencia técnica y gestión de refacciones.")

# Inicializar y cargar la base de datos (se ejecuta una sola vez para optimizar)
@st.cache_resource
def inicializar_sistema():
    # Asegúrate de usar la ruta correcta a tu JSON
    base_datos = cargar_base_conocimiento('data/base_conocimiento.json')
    return base_datos

try:
    base_datos = inicializar_sistema()
    st.success("✅ Base de conocimiento automotriz cargada localmente.")
except Exception as e:
    st.error(f"❌ Error al cargar la base de conocimiento: {e}")

st.divider()

# Entrada de texto del usuario
entrada_usuario = st.text_area(
    "Describe detalladamente los síntomas de tu vehículo o introduce los códigos OBD-II (Ej: P0300):",
    placeholder="Ej: Tengo un nissan versa que tiembla mucho en los semáforos y avienta humo negro..."
)

# Botón para ejecutar el diagnóstico
if st.button("🔧 Generar Diagnóstico Experto"):
    if not entrada_usuario.strip():
        st.warning("Por favor, describe una falla o introduce un código antes de continuar.")
    else:
        with st.spinner("Analizando síntomas semánticamente y consultando al motor de inferencia..."):
            try:
                # 1. Recuperación por vectores
                contexto_filtrado = recuperar_contexto_semantico(entrada_usuario, base_datos)
                
                # 2. Generación del reporte con el LLM
                respuesta_final = generar_respuesta_sistema_experto(entrada_usuario, contexto_filtrado)
                
                # 3. Mostrar resultados en pantalla con formato Markdown
                st.markdown("### 📋 Reporte Técnico de Diagnóstico")
                st.markdown(respuesta_final)
                
            except Exception as e:
                st.error(f"Ocurrió un error durante el procesamiento: {e}")

st.divider()
st.caption("Desarrollado como Proyecto de Residencias / Tesis de Ingeniería. v1.0.0 (Híbrido RAG)")