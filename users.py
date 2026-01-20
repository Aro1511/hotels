from firebase_db import db
from auth import hash_password, verify_password
from datetime import datetime
import streamlit as st
from utils import load_language, translator

SUPERADMIN_EMAIL = "admin@hotel.de"

def ensure_superadmin_exists():
    texts = load_language(st.session_state.get("language", "de"))
    t = translator(texts)

    users_ref = db.collection("users")
    query = users_ref.where("role", "==", "superadmin").limit(1).stream()

    exists = False
    for _ in query:
        exists = True

    if exists:
        return True

    st.title(t("superadmin_setup_title"))
    st.info(t("superadmin_setup_info"))

    pw = st.text_input(t("superadmin_password"), type="password")

    if st.button(t("superadmin_create")):
        if not pw:
            st.error("Bitte ein Passwort eingeben.")
            return False

        users_ref.add({
            "email": SUPERADMIN_EMAIL,
            "password_hash": hash_password(pw),
            "role": "superadmin",
            "tenant_id": "superadmin",
            "active": True,
            "created_at": datetime.utcnow()
        })

        st.success("Superadmin wurde erfolgreich erstellt.")
        st.rerun()

    return False


def get_user_by_email(email: str):
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", email).limit(1).stream()
    for doc in query:
        user = doc.to_dict()
        user["id"] = doc.id
        return user
    return None


def validate_login(email: str, password: str):
    if not ensure_superadmin_exists():
        return None

    user = get_user_by_email(email)
    if not user:
        return None
    if not user.get("active", True):
        return None
    if verify_password(password, user["password_hash"]):
        return user
    return None


def create_user(email: str, password: str, role: str, tenant_id: str):
    return db.collection("users").add({
        "email": email,
        "password_hash": hash_password(password),
        "role": role,
        "tenant_id": tenant_id,
        "active": True,
        "created_at": datetime.utcnow()
    })


def deactivate_user(user_id: str):
    db.collection("users").document(user_id).update({"active": False})


def delete_user(user_id: str):
    db.collection("users").document(user_id).delete()


def list_users_by_tenant(tenant_id: str):
    users_ref = db.collection("users").where("tenant_id", "==", tenant_id).stream()
    users = []
    for doc in users_ref:
        u = doc.to_dict()
        u["id"] = doc.id
        users.append(u)
    return users
