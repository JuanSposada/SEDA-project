import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import unicodedata
import os

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS Y BASES DE DATOS
# ==========================================
DB_ORIGEN = 'data/dtc_codes.db' 
DB_DESTINO = 'data/seda_diagnostico.db'

# ==========================================
# 2. LÓGICA DEL SCRAPER INTELIGENTE 
# ==========================================
def normalizar_texto(texto):
    texto_normalizado = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto_normalizado.lower()

# [NUEVO] Agregamos 'errores_comunes' y afinamos 'reparacion'
# NOTA: En Python el orden importa. Ponemos las palabras más específicas primero.
CATEGORIAS_KEYWORDS = {
    "marcas_afectadas": ["marcas", "vehiculos", "modelos"],
    "sintomas": ["sintomas"],
    "causas": ["causas", "motivos", "razones"],
    "errores_comunes": ["errores comunes", "errores al diagnosticar", "errores frecuentes", "equivocaciones"],
    "reparacion": ["reparar", "reparacion", "reparaciones", "yo mismo", "diy", "como arreglar"],
    "soluciones": ["soluciones", "solucionar", "arreglar"], 
    "codigos_relacionados": ["relacionados", "otros codigos"],
    "puedo_manejarlo": ["seguir conduciendo", "conducir", "manejar"],
    "ubicacion": ["donde se encuentra", "ubicacion"],
    "diagnostico": ["diagnostico", "procedimiento"]
}

def identificar_categoria(texto_h2):
    texto_lower = normalizar_texto(texto_h2)
    for categoria, palabras_clave in CATEGORIAS_KEYWORDS.items():
        if any(palabra in texto_lower for palabra in palabras_clave):
            return categoria
    return None

def extraer_y_guardar_obd(codigo_dtc, cursor_destino):
    codigo = codigo_dtc.strip().lower()
    url = f"https://libreriaobd2.com/{codigo}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"[-] {codigo.upper()}: No encontrado en la web.")
            return False
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        datos = {key: "" for key in CATEGORIAS_KEYWORDS.keys()}
        datos["codigo"] = codigo.upper()
        datos["significado"] = ""

        h1 = soup.find('h1')
        if h1:
            parrafos_significado = []
            # Buscar todos los párrafos y subtítulos que estén después del H1 en todo el HTML
            for nodo in h1.find_all_next(['p', 'h2']):
                # Si llegamos a un H2 de nuestras categorías (ej. "Síntomas"), detenemos la búsqueda
                if nodo.name == 'h2' and identificar_categoria(nodo.text):
                    break
                
                # Si es un párrafo, extraemos su texto
                if nodo.name == 'p':
                    texto_p = nodo.text.strip()
                    # Filtramos basura (párrafos muy cortos, fechas, o botones de menú)
                    if texto_p and len(texto_p) > 20 and "Toggle" not in texto_p and "¿Qué encontrarás" not in texto_p:
                        parrafos_significado.append(texto_p)
                        
            datos["significado"] = "\n".join(parrafos_significado)

        encabezados_h2 = soup.find_all('h2')
        for h2 in encabezados_h2:
            categoria_detectada = identificar_categoria(h2.text)
            
            if categoria_detectada and not datos[categoria_detectada]:
                contenido_seccion = []
                nodo_actual = h2.find_next_sibling()
                
                while nodo_actual and getattr(nodo_actual, 'name', None) not in ['h2', 'h1']:
                    nombre_nodo = getattr(nodo_actual, 'name', None)
                    
                    if nombre_nodo in ['ul', 'ol']:
                        for li in nodo_actual.find_all('li'):
                            texto_li = li.get_text(strip=True)
                            if texto_li: contenido_seccion.append(f"- {texto_li}")
                    elif nombre_nodo == 'p':
                        texto_p = nodo_actual.get_text(strip=True)
                        if texto_p: contenido_seccion.append(texto_p)
                    elif nombre_nodo == 'h3':
                        texto_h3 = nodo_actual.get_text(strip=True)
                        if texto_h3: contenido_seccion.append(f"{texto_h3}")
                    elif nombre_nodo == 'div':
                        for tag in nodo_actual.find_all(['p', 'li', 'h3']):
                            texto_tag = tag.get_text(strip=True)
                            if texto_tag:
                                if tag.name == 'li':
                                    contenido_seccion.append(f"- {texto_tag}")
                                else:
                                    contenido_seccion.append(texto_tag)
                                    
                    nodo_actual = nodo_actual.find_next_sibling()
                
                datos[categoria_detectada] = "\n".join(contenido_seccion)

        # [NUEVO] Se añade la inserción de la columna errores_comunes
        cursor_destino.execute('''
            REPLACE INTO obd_informacion (
                codigo, significado, marcas_afectadas, sintomas, causas, 
                soluciones, codigos_relacionados, puedo_manejarlo, reparacion, 
                ubicacion, diagnostico, errores_comunes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datos["codigo"], datos["significado"], datos["marcas_afectadas"], 
            datos["sintomas"], datos["causas"], datos["soluciones"], 
            datos["codigos_relacionados"], datos["puedo_manejarlo"], 
            datos["reparacion"], datos["ubicacion"], datos["diagnostico"],
            datos["errores_comunes"]
        ))
        
        print(f"[+] {codigo.upper()}: Procesado y guardado correctamente.")
        return True

    except requests.exceptions.RequestException as e:
        print(f"[!] {codigo.upper()}: Error de conexión ({e}).")
        return False

# ==========================================
# 3. LÓGICA DE ITERACIÓN MAESTRA
# ==========================================
def iniciar_proceso_etl():
    if not os.path.exists(DB_ORIGEN):
        print(f"Error: No se encontró la base de datos de origen '{DB_ORIGEN}'.")
        return

    conn_origen = sqlite3.connect(DB_ORIGEN)
    cursor_origen = conn_origen.cursor()

    conn_destino = sqlite3.connect(DB_DESTINO)
    cursor_destino = conn_destino.cursor()
    
    # [NUEVO] Actualización de la estructura de la tabla
    cursor_destino.execute('''
        CREATE TABLE IF NOT EXISTS obd_informacion (
            codigo TEXT PRIMARY KEY,
            significado TEXT,
            marcas_afectadas TEXT,
            sintomas TEXT,
            causas TEXT,
            soluciones TEXT,
            codigos_relacionados TEXT,
            puedo_manejarlo TEXT,
            reparacion TEXT,
            ubicacion TEXT,
            diagnostico TEXT,
            errores_comunes TEXT
        )
    ''')
    
    # Intento de agregar la columna dinámicamente por si tu BD ya existe y no la borraste
    try:
        cursor_destino.execute("ALTER TABLE obd_informacion ADD COLUMN errores_comunes TEXT")
    except sqlite3.OperationalError:
        pass # La columna ya existe, continuamos normal
        
    conn_destino.commit()

    cursor_destino.execute("SELECT codigo FROM obd_informacion WHERE significado != '' AND significado IS NOT NULL")
    codigos_ya_procesados = {fila[0] for fila in cursor_destino.fetchall()}

    cursor_origen.execute("SELECT code FROM dtc_definitions") 
    todos_los_codigos = cursor_origen.fetchall()

    codigos_pendientes = [fila[0] for fila in todos_los_codigos if fila[0] not in codigos_ya_procesados]

    print(f"Total de códigos en base original: {len(todos_los_codigos)}")
    print(f"Códigos ya guardados en SEDA: {len(codigos_ya_procesados)}")
    print(f"Códigos pendientes por procesar: {len(codigos_pendientes)}\n")
    print("Iniciando extracción...")

    for codigo in codigos_pendientes:
        exito = extraer_y_guardar_obd(codigo, cursor_destino)
        conn_destino.commit() 
        time.sleep(3) 

    conn_origen.close()
    conn_destino.close()
    print("\n[✔] Proceso ETL finalizado por completo.")

if __name__ == "__main__":
    iniciar_proceso_etl()