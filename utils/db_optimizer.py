import sqlite3

def optimizar_base_datos_avanzada():
    conn = sqlite3.connect('data/seda_diagnostico.db')
    cursor = conn.cursor()
    
    # 1. Índice normal (B-Tree) para búsquedas exactas por código
    print("Verificando índice estándar para códigos...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_codigos_obd_codigo ON obd_informacion(codigo);")
    
    # IMPORTANTE: Borrar rastro de ejecuciones fallidas previas
    print("Limpiando instalaciones previas...")
    cursor.execute("DROP TABLE IF EXISTS busqueda_global;")

    # 2. CREACIÓN DEL SÚPER ÍNDICE FTS5 (Texto Completo)
    print("Creando índice de texto completo (FTS5) para toda la base de conocimientos...")
    
    # TODO EN UNA SOLA LÍNEA Y SIN DUPLICADOS (12 columnas)
    cursor.execute("""
        CREATE VIRTUAL TABLE busqueda_global 
        USING fts5(codigo, significado, marcas_afectadas, sintomas, causas, soluciones, codigos_relacionados, puedo_manejarlo, reparacion, ubicacion, diagnostico, errores_comunes);
    """)
    
    # Sincronizamos los datos especificando claramente de dónde a dónde van
    print("Sincronizando los datos a la tabla virtual...")
    cursor.execute("""
        INSERT INTO busqueda_global (codigo, significado, marcas_afectadas, sintomas, causas, soluciones, codigos_relacionados, puedo_manejarlo, reparacion, ubicacion, diagnostico, errores_comunes)
        SELECT codigo, significado, marcas_afectadas, sintomas, causas, soluciones, codigos_relacionados, puedo_manejarlo, reparacion, ubicacion, diagnostico, errores_comunes
        FROM obd_informacion;
    """)
    
    conn.commit()
    conn.close()
    print("✅ Súper buscador FTS5 creado y poblado con éxito.")

if __name__ == "__main__":
    optimizar_base_datos_avanzada()