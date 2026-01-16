import json
import streamlit as st

@st.cache_data
def load_language(lang: str):
    """
    Lädt die Sprachdatei aus dem Ordner /lang.
    Fällt zurück auf Deutsch, falls Datei fehlt.
    """
    try:
        with open(f"lang/{lang}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        with open("lang/de.json", "r", encoding="utf-8") as f:
            return json.load(f)

def translator(texts: dict):
    """
    Gibt eine Funktion zurück, die Texte anhand eines Keys übersetzt.
    """
    return lambda key: texts.get(key, key)
