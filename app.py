import streamlit as st
import csv
import io
from PIL import Image
import base64
import pandas as pd

from logic import (
    add_room,
    add_guest,
    add_night_to_guest,
    set_night_paid_status,
    calculate_nights_summary,
    search_guests_by_name,
    list_all_guests,
    checkout_guest,
    delete_guest,
)
from database import load_rooms, delete_room, set_room_free
from models import Guest
from utils import load_language, translator
from pdf_generator import generate_receipt_pdf


# ---------------------------------------------------------
# CSS laden
# ---------------------------------------------------------
def load_css():
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        pass


# ---------------------------------------------------------
# Sprache & Grundkonfiguration
# ---------------------------------------------------------
if "language" not in st.session_state:
    st.session_state.language = "de"

lang_choice = st.session_state.get("language", "de")
texts = load_language(lang_choice)
t = translator(texts)

st.set_page_config(
    page_title=t("app_title"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_css()


# ---------------------------------------------------------
# HOTEL-ID (ohne Login)
# ---------------------------------------------------------
if "hotel_id" not in st.session_state:
    st.session_state.hotel_id = "default_hotel"

hotel_id = st.session_state.hotel_id


# ---------------------------------------------------------
# Session-State
# ---------------------------------------------------------
if "open_guest_id" not in st.session_state:
    st.session_state.open_guest_id = None

if "show_rooms" not in st.session_state:
    st.session_state.show_rooms = False

if "show_free_rooms" not in st.session_state:
    st.session_state.show_free_rooms = False

if "auto_open_guest" not in st.session_state:
    st.session_state.auto_open_guest = None

if "guest_form_collapsed" not in st.session_state:
    st.session_state.guest_form_collapsed = False


# ---------------------------------------------------------
# Logo laden
# ---------------------------------------------------------
def image_to_base64(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


# ---------------------------------------------------------
# Moderner Header + Räume-Buttons
# ---------------------------------------------------------
def show_modern_header():
    try:
        logo = Image.open("logo.png")
        encoded = image_to_base64(logo)

        col1, col2 = st.columns([4, 2])

        with col1:
            st.markdown(
                f"""
                <div style="
                    width: 100%;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 15px 20px;
                    background-color: #F5D7B2;
                    border-radius: 12px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    margin-bottom: 25px;
                ">
                    <h1 style="margin: 0; color: #8B4513; font-weight: 700;">
                        {t("header_title")}
                    </h1>
                    <img src="data:image/png;base64,{encoded}" style="width: 140px;">
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            colA, colB = st.columns(2)

            with colA:
                if st.button("Besetzte Räume"):
                    st.session_state.show_rooms = not st.session_state.show_rooms

            with colB:
                if st.button("Freie Räume"):
                    st.session_state.show_free_rooms = not st.session_state.show_free_rooms

    except Exception:
        pass


show_modern_header()


# ---------------------------------------------------------
# Besetzte Räume anzeigen
# ---------------------------------------------------------
def render_rooms_overview():
    if not st.session_state.show_rooms:
        return

    rooms = load_rooms(hotel_id)
    occupied = [r for r in rooms if r.occupied]

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if not occupied:
        st.write("Keine besetzten Räume")
    else:
        st.write(f"Du hast {len(occupied)} besetzte Räume:")
        for r in occupied:
            st.write(f"• Zimmer {r.number} ({r.category})")

    st.markdown("</div>", unsafe_allow_html=True)


render_rooms_overview()


# ---------------------------------------------------------
# Freie Räume anzeigen
# ---------------------------------------------------------
def render_free_rooms():
    if not st.session_state.show_free_rooms:
        return

    rooms = load_rooms(hotel_id)
    free_rooms = [r for r in rooms if not r.occupied]

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if not free_rooms:
        st.write("Keine freien Räume")
    else:
        st.write(f"Du hast {len(free_rooms)} freie Räume:")
        for r in free_rooms:
            st.write(f"• Zimmer {r.number} ({r.category})")

    st.markdown("</div>", unsafe_allow_html=True)


render_free_rooms()
# ---------------------------------------------------------
# Seite: Gästeliste
# ---------------------------------------------------------
def page_gaesteliste():
    st.header("Gästeliste")

    guests = list_all_guests(hotel_id, include_checked_out=False)

    if not guests:
        st.info("Keine Gäste vorhanden")
        return

    if st.session_state.auto_open_guest:
        st.session_state.open_guest_id = st.session_state.auto_open_guest
        st.session_state.auto_open_guest = None

    for guest in guests:
        render_guest_accordion(guest, editable=True)


# ---------------------------------------------------------
# Seite: Suche
# ---------------------------------------------------------
def page_suche():
    st.header("Gäste suchen")

    query = st.text_input("Name eingeben")
    include_checked_out = st.checkbox("Ausgecheckte Gäste einbeziehen", value=False)

    if query:
        results = search_guests_by_name(hotel_id, query)

        if not include_checked_out:
            results = [g for g in results if g.status == "checked_in"]

        if not results:
            st.warning("Keine Ergebnisse")
            return

        for guest in results:
            render_guest_accordion(guest, editable=True)


# ---------------------------------------------------------
# Seite: Zimmerverwaltung
# ---------------------------------------------------------
def page_zimmerverwaltung():
    st.header("Zimmerverwaltung")

    st.subheader("Zimmer hinzufügen")
    col1, col2 = st.columns(2)
    with col1:
        number = st.number_input("Zimmernummer", min_value=1, step=1)
    with col2:
        category = st.selectbox(
            "Zimmerkategorie",
            ["Einzel", "Doppel", "Familie", "Suite", "Sonstige"],
        )

    if st.button("Zimmer speichern"):
        try:
            add_room(hotel_id, int(number), category)
            st.success(f"Zimmer {int(number)} wurde hinzugefügt")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.subheader("Bestehende Zimmer")
    rooms = load_rooms(hotel_id)

    if not rooms:
        st.info("Noch keine Zimmer vorhanden")
    else:
        for r in rooms:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write(f"**Zimmer:** {r.number}")
            st.write(f"**Kategorie:** {r.category}")
            st.write(f"**Status:** {'Belegt' if r.occupied else 'Frei'}")

            colA, colB = st.columns(2)

            with colA:
                if st.button("Zimmer löschen", key=f"delete_room_{r.number}"):
                    delete_room(hotel_id, r.number)
                    st.success("Zimmer gelöscht")
                    st.rerun()

            with colB:
                if r.occupied:
                    if st.button("Zimmer freigeben", key=f"free_room_{r.number}"):
                        set_room_free(hotel_id, r.number)
                        st.success("Zimmer freigegeben")
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Seite: Checkout
# ---------------------------------------------------------
def page_checkout():
    st.header("Ausgecheckte Gäste")

    guests = list_all_guests(hotel_id, include_checked_out=True)
    checked_out = [g for g in guests if g.status == "checked_out"]

    if not checked_out:
        st.info("Keine ausgecheckten Gäste")
        return

    for guest in checked_out:
        render_guest_accordion(guest, editable=False)

        if st.button("Gast löschen", key=f"delete_{guest.id}"):
            delete_guest(hotel_id, guest.id)
            st.success("Gast gelöscht")
            st.rerun()


# ---------------------------------------------------------
# Einfaches Dashboard
# ---------------------------------------------------------
def page_dashboard():
    st.header("Dashboard – Übersicht")

    guests = list_all_guests(hotel_id, include_checked_out=True)
    rooms = load_rooms(hotel_id)

    current_guests = len([g for g in guests if g.status == "checked_in"])
    checked_out = len([g for g in guests if g.status == "checked_out"])
    total_rooms = len(rooms)
    occupied_rooms = len([r for r in rooms if r.occupied])
    free_rooms = total_rooms - occupied_rooms

    revenue = sum(len([n for n in g.nights if n.paid]) * g.price_per_night for g in guests)
    unpaid = sum(len([n for n in g.nights if not n.paid]) * g.price_per_night for g in guests)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Gäste")
    st.write(f"Aktuell eingecheckt: **{current_guests}**")
    st.write(f"Ausgecheckt: **{checked_out}**")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Zimmer")
    st.write(f"Gesamt: **{total_rooms}**")
    st.write(f"Belegt: **{occupied_rooms}**")
    st.write(f"Frei: **{free_rooms}**")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Einnahmen")
    st.write(f"Bezahlte Nächte: **{revenue:.2f} €**")
    st.write(f"Unbezahlte Nächte: **{unpaid:.2f} €**")
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------
def main():
    with st.sidebar:
        st.title("Navigation")

        current_lang = st.session_state.get("language", "de")
        lang_options = {
            "Deutsch": "de",
            "Englisch": "en"
        }
        selected_label = st.radio(
            "Sprache",
            list(lang_options.keys()),
            index=0 if current_lang == "de" else 1
        )
        new_lang = lang_options[selected_label]
        if new_lang != current_lang:
            st.session_state["language"] = new_lang
            st.rerun()

        st.markdown("---")

        page = st.radio(
            "Seite auswählen",
            (
                "Dashboard",
                "Neuen Gast anlegen",
                "Gästeliste",
                "Gäste suchen",
                "Zimmerverwaltung",
                "Ausgecheckte Gäste",
            ),
        )

    if page == "Dashboard":
        page_dashboard()
    elif page == "Neuen Gast anlegen":
        page_neuer_gast()
    elif page == "Gästeliste":
        page_gaesteliste()
    elif page == "Gäste suchen":
        page_suche()
    elif page == "Zimmerverwaltung":
        page_zimmerverwaltung()
    elif page == "Ausgecheckte Gäste":
        page_checkout()


if __name__ == "__main__":
    main()
