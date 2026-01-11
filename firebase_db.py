import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore


# ---------------------------------------------------------
# Firestore-Initialisierung über Streamlit Secrets
# ---------------------------------------------------------
# Secrets laden
firebase_secrets = st.secrets["firebase"]

# WICHTIG: Streamlit liefert ein SectionProxy-Objekt.
# Firebase braucht aber ein echtes Python-Dict.
firebase_creds = dict(firebase_secrets)

# Firebase-App nur einmal initialisieren
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ---------------------------------------------------------
# Hilfsfunktionen: JSON-ähnliche Daten über Firestore speichern/laden
# ---------------------------------------------------------
def load_json(path: str):
    """
    Lädt eine Liste von Objekten aus Firestore.

    path: z.B. "default_hotel/gaeste" oder "default_hotel/raeume"
    Rückgabe: Liste (oder leere Liste, wenn nichts vorhanden)
    """
    doc_ref = db.collection("hotel_app").document(path)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict().get("data")
        if isinstance(data, list):
            return data
    return []


def save_json(path: str, data):
    """
    Speichert eine Liste von Objekten in Firestore.

    path: z.B. "default_hotel/gaeste" oder "default_hotel/raeume"
    data: Liste von dicts
    """
    doc_ref = db.collection("hotel_app").document(path)
    doc_ref.set({"data": data})
