import streamlit as st
from firebase_db import db
from auth import hash_password, verify_password
from datetime import datetime

SUPERADMIN_EMAIL = "admin@hotel.de"


# ---------------------------------------------------------
# Superadmin prüfen / erstellen
# ---------------------------------------------------------
def ensure_superadmin_exists():
    users_ref = db.collection("users")

    # Prüfen, ob bereits ein Superadmin existiert
    existing = list(
        users_ref.where("role", "==", "superadmin").limit(1).stream()
    )
    if existing:
        return True  # Superadmin existiert schon

    # Setup anzeigen
    st.title("Superadmin einrichten")
    st.info("Bitte ein Passwort für den Superadmin festlegen.")

    pw = st.text_input("Superadmin-Passwort", type="password")

    # Sobald ein Passwort eingegeben wurde → speichern
    if pw:
        users_ref.add({
            "email": SUPERADMIN_EMAIL,
            "password_hash": hash_password(pw),
            "role": "superadmin",
            "tenant_id": "superadmin",
            "active": True,
            "created_at": datetime.utcnow()
        })

        st.success("Superadmin wurde erfolgreich erstellt. Bitte erneut einloggen.")
        st.session_state.clear()
        st.rerun()

    # Solange noch kein Passwort eingegeben wurde
    return False


# ---------------------------------------------------------
# Benutzer anhand E-Mail laden
# ---------------------------------------------------------
def get_user_by_email(email: str):
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", email).limit(1).stream()

    for doc in query:
        user = doc.to_dict()
        user["id"] = doc.id
        return user

    return None


# ---------------------------------------------------------
# Login prüfen
# ---------------------------------------------------------
def validate_login(email: str, password: str):
    user = get_user_by_email(email)
    if not user:
        return None

    if not user.get("active", True):
        return None

    # Passwort prüfen
    if verify_password(password, user["password_hash"]):
        return user

    return None


# ---------------------------------------------------------
# Benutzer erstellen
# ---------------------------------------------------------
def create_user(email: str, password: str, role: str, tenant_id: str):
    return db.collection("users").add({
        "email": email,
        "password_hash": hash_password(password),
        "role": role,
        "tenant_id": tenant_id,
        "active": True,
        "created_at": datetime.utcnow()
    })


# ---------------------------------------------------------
# Benutzer deaktivieren
# ---------------------------------------------------------
def deactivate_user(user_id: str):
    db.collection("users").document(user_id).update({"active": False})


# ---------------------------------------------------------
# Benutzer löschen
# ---------------------------------------------------------
def delete_user(user_id: str):
    db.collection("users").document(user_id).delete()


# ---------------------------------------------------------
# Benutzer eines Mandanten auflisten
# ---------------------------------------------------------
def list_users_by_tenant(tenant_id: str):
    users_ref = db.collection("users").where("tenant_id", "==", tenant_id).stream()
    users = []

    for doc in users_ref:
        u = doc.to_dict()
        u["id"] = doc.id
        users.append(u)

    return users
