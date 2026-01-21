import streamlit as st
from firebase_db import db

def main():
    st.title("Superadmin – Verwaltung")

    # ---------------------------------------------------------
    # Benutzer laden
    # ---------------------------------------------------------
    users_ref = db.collection("users").stream()
    users = []

    for doc in users_ref:
        u = doc.to_dict()
        u["id"] = doc.id
        users.append(u)

    st.subheader("Benutzerübersicht")

    # ---------------------------------------------------------
    # Benutzerliste anzeigen
    # ---------------------------------------------------------
    for u in users:
        email = u.get("email", "⚠️ Keine E-Mail")
        role = u.get("role", "unbekannt")
        active = u.get("active", True)

        st.write(f"📧 {email} – Rolle: {role} – Aktiv: {active}")

        col1, col2 = st.columns(2)

        if col1.button("Deaktivieren", key=f"deact_{u['id']}"):
            db.collection("users").document(u["id"]).update({"active": False})
            st.rerun()

        if col2.button("Löschen", key=f"del_{u['id']}"):
            db.collection("users").document(u["id"]).delete()
            st.rerun()

    # ---------------------------------------------------------
    # Neuen Benutzer anlegen
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("Neuen Mandanten / Benutzer anlegen")

    email = st.text_input("E-Mail")
    password = st.text_input("Passwort", type="password")
    role = st.selectbox("Rolle", ["customer", "admin"])
    tenant_id = st.text_input("Tenant-ID")

    if st.button("Benutzer erstellen"):
        if not email or not password or not tenant_id:
            st.error("Bitte alle Felder ausfüllen.")
        else:
            from users import create_user
            create_user(email, password, role, tenant_id)
            st.success("Benutzer erstellt.")
            st.rerun()
