import sqlite3
import json
import random
from pathlib import Path

# Directorios del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "seda_diagnostico.db"
OUTPUT_JSONL = BASE_DIR / "data" / "dataset_seda_sft.jsonl"

SYSTEM_PROMPT = (
    "Eres SEDA (Sistema Experto de Diagnóstico Automotriz), un Ingeniero Automotriz Maestro de nivel senior. "
    "Tu objetivo es emitir reportes de diagnóstico técnico exhaustivos, fundamentados en códigos OBD-II, manuales de taller y catálogos de refacciones."
)

MARCAS_POPULARES = [
    ("Honda", ["Civic", "Accord", "CR-V", "Fit"]),
    ("Toyota", ["Corolla", "Camry", "RAV4", "Hilux", "Yaris"]),
    ("Nissan", ["Versa", "Sentra", "Tsuru", "March", "Altima"]),
    ("Acura", ["TL", "Integra", "MDX", "RSX"]),
    ("Ford", ["F-150", "Focus", "Fiesta", "Explorer", "Mustang"]),
    ("Chevrolet", ["Chevy", "Aveo", "Silverado", "Spark", "Cruze"]),
    ("Volkswagen", ["Jetta", "Golf", "Vento", "Polo"])
]

def obtener_datos_bd():
    """Extrae todos los registros enriquecidos de la base de datos."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT codigo, significado, marcas_afectadas, sintomas, causas, 
                   soluciones, puedo_manejarlo, reparacion, ubicacion, diagnostico, errores_comunes
            FROM obd_informacion
        """)
        return [dict(row) for row in cursor.fetchall()]

def formatear_asistente(item, make, model, year):
    """Genera la respuesta del reporte de diagnóstico de acuerdo al estándar de SEDA."""
    codigo = item.get("codigo", "")
    significado = item.get("significado", "")
    sintomas = item.get("sintomas", "Falla en el rendimiento del motor")
    causas = item.get("causas", "Componente defectuoso o daño en arnés eléctrico")
    soluciones = item.get("soluciones", "Revisión técnica y reemplazo de componente")
    puedo_manejarlo = item.get("puedo_manejarlo", "Se recomienda no conducir distancias largas hasta verificar la gravedad.")
    reparacion = item.get("reparacion", "Inspección de voltajes y continuidad con multímetro.")

    reporte = f"""# 🚗 Reporte de Diagnóstico SEDA: {year} {make} {model}

## 1. 🔍 Resumen del Diagnóstico y Código de Falla
- **Código / Falla Identificada:** {codigo} - {significado}
- **Causa Raíz Principal:** {causas}
- **Ficha del Vehículo:** {year} {make} {model}

## 2. ⚠️ Evaluación de Seguridad y Manejo del Vehículo
- **¿Es seguro conducirlo?:** {puedo_manejarlo}
- **Riesgos de Daño Mayor:** Ignorar esta falla puede provocar daños mayores en el sistema de combustión, emisión o catalizador.

## 3. 🛠️ Guía Paso a Paso de Pruebas y Reparación
- **Inspección Básica (Para el Conductor):**
{sintomas}
- **Procedimiento de Taller (Técnico Automotriz):**
{reparacion}
{soluciones}

## 4. 🛒 Refacciones y Componentes Compatibles
- **Componentes sugeridos para revisión/reemplazo:** Piezas asociadas al circuito de {codigo}. Consultar refaccionaria local para compatibilidad exacta por número de chasis/VIN.

## 5. 💡 Conclusión y Recomendación del Ingeniero
Se recomienda escanear y borrar códigos tras la reparación, seguido de una prueba de manejo para confirmar la solución definitiva de la falla.
"""
    return reporte.strip()

def generar_dataset():
    print(f"[SEDA Dataset] Conectando a {DB_PATH}...")
    filas = obtener_datos_bd()
    print(f"[SEDA Dataset] Se encontraron {len(filas)} códigos enriquecidos en la base de datos.")

    dataset = []

    for item in filas:
        codigo = item.get("codigo", "")
        sintomas = item.get("sintomas", "")
        
        # Generar combinación de vehículo aleatoria
        make, modelos = random.choice(MARCAS_POPULARES)
        model = random.choice(modelos)
        year = str(random.randint(1998, 2023))

        # Variación A: Consulta Directa por Código DTC
        prompt_user_dtc = f"Tengo un {year} {make} {model} y el escáner me arrojó el código de falla {codigo}. ¿Cuál es el diagnóstico y solución?"
        asistente_dtc = formatear_asistente(item, make, model, year)

        dataset.append({
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt_user_dtc},
                {"role": "assistant", "content": asistente_dtc}
            ]
        })

        # Variación B: Consulta por Síntomas (si hay descripción de síntomas)
        if sintomas and len(sintomas.strip()) > 10:
            sintoma_resumen = sintomas.replace("\n", " ")[:120]
            prompt_user_sintomas = f"Mi auto es un {year} {make} {model} y presenta la siguiente falla: {sintoma_resumen}. ¿Qué problema tiene?"
            dataset.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_user_sintomas},
                    {"role": "assistant", "content": asistente_dtc}
                ]
            })

    # Mezclar y guardar en archivo JSONL
    random.shuffle(dataset)
    
    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for entry in dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"✅ [Éxito] Dataset de Fine-Tuning generado exitosamente con {len(dataset)} pares de entrenamiento.")
    print(f"📁 Archivo guardado en: {OUTPUT_JSONL}")

if __name__ == "__main__":
    generar_dataset()
