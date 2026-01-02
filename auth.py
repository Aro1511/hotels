import hashlib
import os
from firebase_admin import firestore

db = firestore.client()


def _hash_password(password: str, salt: str) -> str:
    """
    Erzeugt einen Hash aus Passwort + Salt.
    Format: salt$hash
    """
    h = hashlib.sha256()
    h.update((salt + password).encode("utf-8"))
    return h.hexdigest()


# ---------------------------------------------------------
# 1. Benutzer anlegen (Hotel registrieren)
# ---------------------------------------------------------
def create_user(hotel_id: str, password: str):
    """
    Legt ein neues Hotel mit Passwort an.
    Passwort wird als salt$hash gespeichert.
    """
    doc_ref = db.collection("users").document(hotel_id)

    if doc_ref.get().exists:
        raise ValueError("Hotel-ID existiert bereits!")

    salt = os.urandom(16).hex()
    password_hash = _hash_password(password, salt)
    stored_value = f"{salt}${password_hash}"

    doc_ref.set({
        "password_hash": stored_value
    })


# ---------------------------------------------------------
# 2. Benutzer laden
# ---------------------------------------------------------
def get_user(hotel_id: str):
    doc = db.collection("users").document(hotel_id).get()
    if doc.exists:
        return doc.to_dict()
    return None


# ---------------------------------------------------------
# 3. Passwort prüfen
# ---------------------------------------------------------
def verify_password(password: str, stored: str) -> bool:
    """
    stored hat das Format: salt$hash
    """
    try:
        salt, correct_hash = stored.split("$", 1)
    except ValueError:
        return False

    test_hash = _hash_password(password, salt)
    return test_hash == correct_hash


# ---------------------------------------------------------
# 4. Passwort ändern
# ---------------------------------------------------------
def update_password(hotel_id: str, new_password: str):
    doc_ref = db.collection("users").document(hotel_id)

    if not doc_ref.get().exists:
        raise ValueError("Hotel-ID existiert nicht!")

    salt = os.urandom(16).hex()
    password_hash = _hash_password(new_password, salt)
    stored_value = f"{salt}${password_hash}"

    doc_ref.update({
        "password_hash": stored_value
    })


# ---------------------------------------------------------
# 5. Benutzer löschen
# ---------------------------------------------------------
def delete_user(hotel_id: str):
    doc_ref = db.collection("users").document(hotel_id)

    if not doc_ref.get().exists:
        raise ValueError("Hotel-ID existiert nicht!")

    doc_ref.delete()
