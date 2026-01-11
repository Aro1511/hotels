import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore


# ---------------------------------------------------------
# Firestore-Initialisierung über Streamlit Secrets
# ---------------------------------------------------------
firebase_secrets = st.secrets["firebase"]
firebase_creds = dict(firebase_secrets)

if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ---------------------------------------------------------
# Firestore-Struktur:
# hotel_app (Collection)
#   └── <hotel_id> (Document)
#         └── <subpath> (Collection: "gaeste" oder "raeume")
#               └── data (Document)
# ---------------------------------------------------------

def load_json(path: str):
    hotel_id, subpath = path.split("/")  # z.B. "default_hotel", "gaeste"

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


def save_json(path: str, data):
    hotel_id, subpath = path.split("/")

    doc_ref = (
        db.collection("hotel_app")
          .document(hotel_id)
          .collection(subpath)
          .document("data")
    )

    doc_ref.set({"data": data})
