import streamlit as st
from auth import create_user, update_password, delete_user

def admin_page():
    st.title("Admin-Bereich")

    st.subheader("Neues Hotel anlegen")
    new_id = st.text_input("Neue Hotel-ID")
    new_pw = st.text_input("Passwort", type="password")

    if st.button("Hotel anlegen"):
        try:
            create_user(new_id, new_pw)
            st.success("Hotel erfolgreich angelegt.")
        except Exception as e:
            st.error(str(e))

    st.markdown("---")

    st.subheader("Passwort ändern")
    pw = st.text_input("Neues Passwort", type="password", key="pw_change")

    if st.button("Passwort ändern"):
        try:
            update_password(st.session_state.hotel_id, pw)
            st.success("Passwort geändert.")
        except Exception as e:
            st.error(str(e))

    st.markdown("---")

    st.subheader("Hotel löschen")
    if st.button("Hotel löschen"):
        try:
            delete_user(st.session_state.hotel_id)
            st.success("Hotel gelöscht.")
        except Exception as e:
            st.error(str(e))
