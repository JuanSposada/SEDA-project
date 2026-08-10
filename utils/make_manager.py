# Mapeo de submarcas a marcas padre oficiales en la base de datos DTC
SUBMAKE_TO_MAKE = {
    "scion": "toyota",
    "lexus": "toyota",
    "daihatsu": "toyota",
    "acura": "honda",
    "infiniti": "nissan",
    "datsun": "nissan",
    "lincoln": "ford",
    "mercury": "ford",
    "buick": "general motors",
    "gmc": "general motors",
    "cadillac": "general motors",
    "chevrolet": "general motors",
    "genesis": "hyundai",
    "kia": "hyundai",  # A veces comparten plataformas del grupo Hyundai-Kia
    "mini": "bmw",
    "rolls-royce": "bmw",
    "smart": "mercedes-benz",
    "maybach": "mercedes-benz",
    "cupra": "volkswagen",
    "seat": "volkswagen",
    "skoda": "volkswagen",
    "audi": "volkswagen",
    "porsche": "volkswagen",
    "bentley": "volkswagen",
    "lamborghini": "volkswagen"
}



def get_make_for_search(make: str, available_makes_in_db: list) -> str:
    """
    Verifica si la marca ingresada existe en la base de datos.
    Si no existe, busca su marca padre. Si tampoco está, devuelve la original 
    o la trata como genérica (SAE).
    """
    clean_make = make.strip().lower()

    if clean_make in available_makes_in_db:
        return clean_make  # La marca existe en la base de datos

    # Si no está, intentamos encontrar su marca padre
    if clean_make in SUBMAKE_TO_MAKE:
        parent_make = SUBMAKE_TO_MAKE[clean_make]
        print(f"Marca '{make}' no encontrada en la base de datos. Usando marca padre: '{parent_make}'.")
        if parent_make in available_makes_in_db:
            return parent_make  # Retorna la marca padre si está en la base de datos

    return clean_make  # Retorna la marca original si no hay coincidencia
