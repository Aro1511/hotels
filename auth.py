import bcrypt
from firebase_admin import firestore

db = firestore.client()

# ---------------------------------------------------------
# 1. Benutzer anlegen (Hotel registrieren)
# ---------------------------------------------------------
def create_user(hotel_id: str, password: str):
    doc_ref = db.collection("users").document(hotel_id)

    if doc_ref.get().exists:
        raise ValueError("Hotel-ID existiert bereits!")

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    doc_ref.set({
        "password_hash": password_hash
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
def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# ---------------------------------------------------------
# 4. Passwort ändern
# ---------------------------------------------------------
def update_password(hotel_id: str, new_password: str):
    doc_ref = db.collection("users").document(hotel_id)

    if not doc_ref.get().exists:
        raise ValueError("Hotel-ID existiert nicht!")

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    doc_ref.update({
        "password_hash": new_hash
    })


# ---------------------------------------------------------
# 5. Benutzer löschen
# ---------------------------------------------------------
def delete_user(hotel_id: str):
    doc_ref = db.collection("users").document(hotel_id)

    if not doc_ref.get().exists:
        raise ValueError("Hotel-ID existiert nicht!")

    doc_ref.delete()
