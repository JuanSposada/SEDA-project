import asyncio
import sys
from rockauto_api import RockAutoClient

async def probar_arbol_rockauto(make="ACURA", year=2000, model="TL"):
    print("="*60)
    print(f" 🚗 PRUEBA COMPLETA DEL ÁRBOL DE NAVEGACIÓN DE ROCKAUTO")
    print(f"    Vehículo Objetivo: {year} {make} {model}")
    print("="*60 + "\n")

    async with RockAutoClient() as client:
        # Nivel 1: Obtención de Fabricantes (Makes)
        print("[NIVEL 1] Consultando Fabricantes Disponibles en RockAuto...")
        try:
            makes_obj = await client.get_makes()
            makes_list = [m.name for m in makes_obj.makes] if makes_obj else []
            print(f"  -> Total Fabricantes encontrados: {len(makes_list)}")
            print(f"  -> Ejemplo de Marcas: {makes_list[:10]}\n")
        except Exception as e:
            print(f"  ❌ Error al consultar marcas: {e}\n")

        # Nivel 2: Obtención de Años para la Marca
        print(f"[NIVEL 2] Consultando Años disponibles para la marca '{make}'...")
        try:
            years_obj = await client.get_years_for_make(make)
            years_list = [y.year for y in years_obj.years] if (years_obj and hasattr(years_obj, 'years')) else []
            print(f"  -> Años disponibles ({make}): {years_list[:15]}...\n")
        except Exception as e:
            print(f"  ❌ Error al consultar años para {make}: {e}\n")

        # Nivel 3: Obtención de Modelos para Marca y Año
        print(f"[NIVEL 3] Consultando Modelos disponibles para '{make}' en el año {year}...")
        try:
            models_obj = await client.get_models_for_make_year(make, int(year))
            models_list = [m.name for m in models_obj.models] if (models_obj and hasattr(models_obj, 'models')) else []
            print(f"  -> Modelos encontrados ({year} {make}): {models_list}\n")
        except Exception as e:
            print(f"  ❌ Error al consultar modelos para {year} {make}: {e}\n")

        # Nivel 4: Creación del Objeto Vehículo
        print(f"[NIVEL 4] Instanciando Objeto Vehículo '{year} {make} {model}'...")
        try:
            vehicle = await client.get_vehicle(make=make, year=int(year), model=model)
            print(f"  -> Vehículo Creado Exitosamente: {vehicle}")
            print(f"  -> CarCode Interno asignado por RockAuto: {getattr(vehicle, 'carcode', 'N/A')}\n")
        except Exception as e:
            print(f"  ❌ Error al instanciar vehículo: {e}\n")
            return

        # Nivel 5: Obtención de Categorías de Refacciones
        print(f"[NIVEL 5] Consultando Categorías Principales de Partes...")
        try:
            categories_obj = await vehicle.get_part_categories()
            categories = categories_obj.categories if categories_obj else []
            print(f"  -> Total Categorías principales encontradas: {len(categories)}")
            for cat in categories:
                print(f"     • Categoría: '{cat.name}' | GroupName: '{cat.group_name}' | Href: '{cat.href}'")
            print()
        except Exception as e:
            print(f"  ❌ Error al obtener categorías: {e}\n")
            return

        # Nivel 6: Inspección de Refacciones por Categorías Seleccionadas
        print(f"[NIVEL 6] Inspeccionando Refacciones en Categorías Clave ('Exhaust & Emission' y 'Fuel & Air')...\n")
        categorias_a_inspeccionar = ["Exhaust & Emission", "Fuel & Air"]

        for cat_name in categorias_a_inspeccionar:
            print(f"--- Inspeccionando Categoría: '{cat_name}' ---")
            try:
                await asyncio.sleep(0.3)
                parts_result = await vehicle.get_parts_by_category(cat_name)
                if parts_result and parts_result.parts:
                    print(f"  -> Total de subcomponentes encontrados: {parts_result.count}")
                    for part in list(parts_result.parts)[:6]:
                        p_name = getattr(part, 'name', 'N/A')
                        p_url = getattr(part, 'url', 'N/A')
                        if p_url and p_url.startswith("/"):
                            p_url = f"https://www.rockauto.com{p_url}"
                        print(f"     - Nombre Pieza: {p_name}")
                        print(f"       Enlace Catálogo: {p_url}")
                else:
                    print(f"  -> No se encontraron partes en la categoría '{cat_name}'.")
                print()
            except Exception as e:
                print(f"  ❌ Error al extraer partes de '{cat_name}': {e}\n")

if __name__ == "__main__":
    make = sys.argv[1] if len(sys.argv) > 1 else "ACURA"
    year = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
    model = sys.argv[3] if len(sys.argv) > 3 else "TL"

    asyncio.run(probar_arbol_rockauto(make, year, model))
