import sqlite3

conexion = sqlite3.connect('./data/dtc_codes.db')
cursor = conexion.cursor()

cursor.execute('CREATE INDEX IF NOT EXISTS idx_dtc_code_real ON dtc_definitions(code)')
conexion.commit()
conexion.close()

print("Optimizacion completada. 'dtc_codes.db' indexada")