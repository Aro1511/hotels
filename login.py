import streamlit as st
from users import validate_login
from utils import load_language, translator

def main():
    # ---------------------------------------------------------
    # Sprache laden
    # ---------------------------------------------------------
    lang = st.session_state.get("language", "de")
    texts = load_language(lang)
    t = translator(texts)

    st.set_page_config(page_title=t("app_title"), layout="centered")

    # ---------------------------------------------------------
    # Login-Formular
    # ---------------------------------------------------------
    st.title(t("login_title"))

    email = st.text_input(t("email"))
    password = st.text_input(t("password"), type="password")

    if st.button(t("login_button")):
        user = validate_login(email, password)

        if not user:
            st.error("Login fehlgeschlagen.")
            return

        # Benutzer speichern
        st.session_state["user"] = user
        st.success("Login erfolgreich.")

        # Kein switch_page → wir nutzen rerun
        st.rerun()

    # ---------------------------------------------------------
    # Sprache wechseln
    # ---------------------------------------------------------
    st.markdown("---")
    lang_options = {
        "Deutsch": "de",
        "Englisch": "en"
    }

    selected_label = st.radio(
        t("language"),
        list(lang_options.keys()),
        index=0 if lang == "de" else 1
    )

    new_lang = lang_options[selected_label]
    if new_lang != lang:
        st.session_state["language"] = new_lang
        st.rerun()


if __name__ == "__main__":
    main()
