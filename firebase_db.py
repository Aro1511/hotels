import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# ---------------------------------------------------------
# Firestore initialisieren
# ---------------------------------------------------------
firebase_secrets = st.secrets["firebase"]
firebase_creds = dict(firebase_secrets)

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------------------------------------------
# Hilfsfunktion: Pfad validieren
# ---------------------------------------------------------
def _parse_path(path: str):
    parts = path.split("/")
    if len(parts) != 2:
        raise ValueError(f"Ungültiger Pfad: {path}. Erwartet: '<hotel_id>/<subpath>'")
    return parts[0], parts[1]

# ---------------------------------------------------------
# Sicherstellen, dass hotel_id-Dokument existiert
# ---------------------------------------------------------
def _ensure_hotel_document(hotel_id: str):
    doc_ref = db.collection("hotel_app").document(hotel_id)
    if not doc_ref.get().exists:
        doc_ref.set({"created": True})

# ---------------------------------------------------------
# JSON laden
# ---------------------------------------------------------
def load_json(path: str):
    hotel_id, subpath = _parse_path(path)

    _ensure_hotel_document(hotel_id)

    doc_ref = (
        db.collection("hotel_app")
          .document(hotel_id)
          .collection(subpath)
          .document("data")
    )

    doc = doc_ref.get()

    if doc.exists:
        data = doc.to_dict().get("data")
        if isinstance(data, list):
            return data

    return []

# ---------------------------------------------------------
# JSON speichern
# ---------------------------------------------------------
def save_json(path: str, data):
    hotel_id, subpath = _parse_path(path)

    _ensure_hotel_document(hotel_id)

    doc_ref = (
        db.collection("hotel_app")
          .document(hotel_id)
          .collection(subpath)
          .document("data")
    )

    doc_ref.set({"data": data})
