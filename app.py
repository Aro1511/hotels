import streamlit as st
from users import validate_login, ensure_superadmin_exists
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
    # Wenn bereits eingeloggt → Hotel-App laden
    # ---------------------------------------------------------
if "user" in st.session_state:
    if st.session_state["user"]["role"] == "superadmin":
        import superadmin_app
        superadmin_app.main()
        return
    else:
        import hotel_app
        hotel_app.main()
        return
    # ---------------------------------------------------------
    # Superadmin prüfen
    # ---------------------------------------------------------
    if not ensure_superadmin_exists():
        return

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
        st.rerun()

    # ---------------------------------------------------------
    # Sprache wechseln
    # ---------------------------------------------------------
    st.markdown("---")
    lang_options = {
        t("german"): "de",
        t("english"): "en"
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
