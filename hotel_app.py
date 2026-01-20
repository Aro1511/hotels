import streamlit as st
import csv
import io
from PIL import Image
import base64

# ---------------------------------------------------------
# LOGIN-PRÜFUNG
# ---------------------------------------------------------
if "user" not in st.session_state:
    st.write("Bitte zuerst einloggen…")
    st.stop()

user = st.session_state["user"]

if user.get("role") != "customer":
    st.error("Nur Kunden können diese Seite nutzen.")
    st.stop()

hotel_id = user["tenant_id"]

# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------
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
# CSS
# ---------------------------------------------------------
def load_css():
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass


# ---------------------------------------------------------
# SPRACHE
# ---------------------------------------------------------
if "language" not in st.session_state:
    st.session_state.language = "de"

texts = load_language(st.session_state.language)
t = translator(texts)

st.set_page_config(page_title=t("app_title"), layout="wide")
load_css()


# ---------------------------------------------------------
# SESSION-STATE
# ---------------------------------------------------------
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

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
# LOGO
# ---------------------------------------------------------
def image_to_base64(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
def show_header():
    try:
        logo = Image.open("logo.png")
        encoded = image_to_base64(logo)

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
    except:
        st.title(t("header_title"))


show_header()


# ---------------------------------------------------------
# RÄUME ANZEIGEN
# ---------------------------------------------------------
def render_rooms():
    if not st.session_state.show_rooms:
        return

    rooms = load_rooms(hotel_id)
    occupied = [r for r in rooms if r.occupied]

    st.subheader("Besetzte Räume")

    if not occupied:
        st.info("Keine besetzten Räume")
    else:
        for r in occupied:
            st.write(f"• Zimmer {r.number} ({r.category})")


def render_free_rooms():
    if not st.session_state.show_free_rooms:
        return

    rooms = load_rooms(hotel_id)
    free = [r for r in rooms if not r.occupied]

    st.subheader("Freie Räume")

    if not free:
        st.info("Keine freien Räume")
    else:
        for r in free:
            st.write(f"• Zimmer {r.number} ({r.category})")


# ---------------------------------------------------------
# GASTDETAILS
# ---------------------------------------------------------
def render_guest_accordion(guest: Guest, editable=True):
    gid = guest.id
    is_open = st.session_state.open_guest_id == gid

    label = ("▾ " if is_open else "▸ ") + guest.name

    if st.button(label, key=f"guest_{gid}"):
        st.session_state.open_guest_id = None if is_open else gid
        st.rerun()

    if not is_open:
        return

    st.write(f"Zimmer: {guest.room_number} ({guest.room_category})")
    st.write(f"Preis pro Nacht: {guest.price_per_night} €")
    st.write(f"Check-in: {guest.checkin_date}")
    if guest.checkout_date:
        st.write(f"Check-out: {guest.checkout_date}")

    st.write("### Nächte")

    for n in guest.nights:
        col1, col2, col3 = st.columns([1, 1, 2])
        col1.write(n.number)
        col2.write("Ja" if n.paid else "Nein")

        if editable:
            if n.paid:
                if col3.button("Als unbezahlt markieren", key=f"unpaid_{gid}_{n.number}"):
                    set_night_paid_status(hotel_id, gid, n.number, False)
                    st.rerun()
            else:
                if col3.button("Als bezahlt markieren", key=f"paid_{gid}_{n.number}"):
                    set_night_paid_status(hotel_id, gid, n.number, True)
                    st.rerun()

    st.write("### Aktionen")

    if editable and guest.status == "checked_in":
        if st.button("Gast auschecken", key=f"checkout_{gid}"):
            checkout_guest(hotel_id, gid)
            st.success("Gast ausgecheckt")
            st.rerun()


# ---------------------------------------------------------
# SEITEN
# ---------------------------------------------------------
def page_dashboard():
    st.header("Dashboard")

    guests = list_all_guests(hotel_id, include_checked_out=True)
    rooms = load_rooms(hotel_id)

    st.write(f"Aktuell eingecheckt: {len([g for g in guests if g.status=='checked_in'])}")
    st.write(f"Ausgecheckt: {len([g for g in guests if g.status=='checked_out'])}")
    st.write(f"Zimmer gesamt: {len(rooms)}")


def page_new_guest():
    st.header("Neuen Gast anlegen")

    name = st.text_input("Name")
    room = st.number_input("Zimmernummer", min_value=1)
    category = st.selectbox("Kategorie", ["Einzel", "Doppel", "Familie", "Suite"])
    price = st.number_input("Preis pro Nacht", min_value=0.0)

    if st.button("Speichern"):
        if not name:
            st.error("Name erforderlich")
        else:
            add_guest(hotel_id, name, int(room), category, float(price))
            st.success("Gast gespeichert")


def page_guest_list():
    st.header("Gästeliste")

    guests = list_all_guests(hotel_id, include_checked_out=False)

    if not guests:
        st.info("Keine Gäste")
        return

    for g in guests:
        render_guest_accordion(g)


def page_search():
    st.header("Suche")

    q = st.text_input("Name eingeben")

    if q:
        results = search_guests_by_name(hotel_id, q)
        if not results:
            st.warning("Keine Ergebnisse")
        else:
            for g in results:
                render_guest_accordion(g)


def page_rooms():
    st.header("Zimmerverwaltung")

    number = st.number_input("Zimmernummer", min_value=1)
    category = st.selectbox("Kategorie", ["Einzel", "Doppel", "Familie", "Suite"])

    if st.button("Zimmer speichern"):
        add_room(hotel_id, int(number), category)
        st.success("Zimmer gespeichert")
        st.rerun()

    st.subheader("Bestehende Zimmer")
    rooms = load_rooms(hotel_id)

    for r in rooms:
        st.write(f"Zimmer {r.number} – {r.category} – {'Belegt' if r.occupied else 'Frei'}")


def page_checkout():
    st.header("Ausgecheckte Gäste")

    guests = list_all_guests(hotel_id, include_checked_out=True)
    checked_out = [g for g in guests if g.status == "checked_out"]

    if not checked_out:
        st.info("Keine ausgecheckten Gäste")
        return

    for g in checked_out:
        render_guest_accordion(g, editable=False)


# ---------------------------------------------------------
# NAVIGATION
# ---------------------------------------------------------
def main():
    with st.sidebar:
        st.title("Navigation")

        if st.button("Abmelden"):
            st.session_state.clear()
            st.rerun()

        st.markdown("---")

        st.session_state.page = st.radio(
            "Seite",
            [
                "Dashboard",
                "Neuen Gast anlegen",
                "Gästeliste",
                "Gäste suchen",
                "Zimmerverwaltung",
                "Ausgecheckte Gäste",
            ],
            index=[
                "Dashboard",
                "Neuen Gast anlegen",
                "Gästeliste",
                "Gäste suchen",
                "Zimmerverwaltung",
                "Ausgecheckte Gäste",
            ].index(st.session_state.page),
        )

    if st.session_state.page == "Dashboard":
        page_dashboard()
    elif st.session_state.page == "Neuen Gast anlegen":
        page_new_guest()
    elif st.session_state.page == "Gästeliste":
        page_guest_list()
    elif st.session_state.page == "Gäste suchen":
        page_search()
    elif st.session_state.page == "Zimmerverwaltung":
        page_rooms()
    elif st.session_state.page == "Ausgecheckte Gäste":
        page_checkout()


if __name__ == "__main__":
    main()
