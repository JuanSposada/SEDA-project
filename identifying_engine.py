import sqlite3
import spacy

# Loading English light NLP model

nlp = spacy.load("en_core_web_sm")

def get_dtc_description(db_path, code, manufacturer=None):
    """Looks up for the DTC conde into SQLite DB"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()


    if manufacturer:
        query = "SELECT description, manufacturer, is_generic FROM dtc_definitions WHERE UPPER(code) = ? and UPPER(manufacturer) = ?"
        cursor.execute(query, (code.upper(), manufacturer.upper()))
    else:
        query = "SELECT description, manufacturer, is_generic FROM dtc_definitions WHERE UPPER(code) = ?"
        cursor.execute(query,(code.upper(),))
    
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "description": result[0],
            "manufacturer": result[1],
            "is_generic": result[2]
            }
    return None

def extract_keywords_nlp(description):
    """Processing technical description using NLP to extract key components"""
    doc = nlp(description)

    # Noisy or diagnosis words that are not car parts"
    noise_words = [
        "circuit", 
        "range",
        "performance",
        "malfunction",
        "low",
        "high",
        "open",
        "short",
        "input",
        "output",
    ]

    keywords = []

    # Analizing NOUS and PROPN that represent car pieces
    for token in doc:
        if (
            token.pos_ in ["NOUN", "PROPN"]
            and token.text.lower() not in noise_words
        ):
            # Saving word in lemma base form
            keywords.append(token.lemma_.upper())

    # Extracting Noun chunks for major precission
    components = []
    for chunk in doc.noun_chunks:
        # Cleaning up elimitatings noisy words
        clean_chunk = [
            word.text
            for word in chunk
            if word.text.lower() not in noise_words and not word.is_stop
        ]
        if clean_chunk:
            components.append(" ".join(clean_chunk).upper())
    
    return {"individual_keywords": keywords, "detected_components": components}

if __name__ == "__main__":
    # Path to the db
    PATH_DB = "/home/sebastian/residencias/SEDA/data/dtc_codes.db"

    # Simulating  user's entry
    dtc_code_input = "P1201"
    manufacturer_input = "ACURA"

    # 1. Looking up into DB
    dtc_info = get_dtc_description(
        PATH_DB, dtc_code_input, manufacturer_input
    )

    if dtc_info:
        print(f"Code: {dtc_code_input}")
        print(f"Original Description: {dtc_info['description']}\n")

        # 2. Applying NLP for description understanding
        analisis = extract_keywords_nlp(dtc_info["description"])

        print("--- AI analisis ---")
        print(f"Keywords: {analisis['individual_keywords']}")
        print(f"Detected Components: {analisis['detected_components']}")
        
        # Business Logic explanation
        print("\n[Business Logic]:")
        print(f"Sistem will find pieces into the inventory that match with: {analisis['detected_components']}")
    else:
        print("Code not found into Local DB")