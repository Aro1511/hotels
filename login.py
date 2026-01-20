import streamlit as st
from users import validate_login
from utils import load_language, translator

def main():
    lang = st.session_state.get("language", "de")
    texts = load_language(lang)
    t = translator(texts)

    st.title(t("login_title"))

    email = st.text_input(t("email"))
    password = st.text_input(t("password"), type="password")

    if st.button(t("login_button")):
        user = validate_login(email, password)
        if not user:
            st.error("Login fehlgeschlagen.")
            return

        st.session_state["user"] = user

        if user["role"] == "superadmin":
            st.switch_page("admin_dashboard.py")
        else:
            st.switch_page("app.py")

if __name__ == "__main__":
    main()
