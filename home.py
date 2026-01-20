import streamlit as st

# Wenn kein User eingeloggt ist → Login anzeigen
if "user" not in st.session_state:
    import login
    login.main()
else:
    import app
    app.main()
