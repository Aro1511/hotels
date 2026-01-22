import streamlit as st
import csv
import io
from PIL import Image
import base64

# ---------------------------------------------------------
# SESSION-STATE INITIALISIERUNG
# ---------------------------------------------------------
DEFAULTS = {
    "page": "Dashboard",
    "open_guest_id": None,
    "show_rooms": False,
    "show_free_rooms": False,
    "auto_open_guest": None,
    "guest_form_collapsed": False,
}

def init_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------
# LOGIN-PRÜFUNG
# ---------------------------------------------------------
if "user" not in st.session_state or not st.session_state["user"]:
    st.write("Bitte zuerst einloggen…")
    st.stop()

# User stabilisieren (wichtig!)
user = st.session_state.get("user")
if not user:
    st.error("Benutzer verloren – bitte erneut einloggen.")
    st.stop()

# Mandant bestimmen
hotel_id = user.get("tenant_id")
if not hotel_id:
    st.error("Fehler: Kein Mandant (tenant_id) gefunden.")
    st.stop()


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
# CSS LADEN
# ---------------------------------------------------------
def load_css():
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass


if "language" not in st.session_state:
    st.session_state.language = "de"

texts = load_language(st.session_state.language)
t = translator(texts)

st.set_page_config(page_title=t("app_title"), layout="wide")
load_css()


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
def image_to_base64(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


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

# Benutzerinfo anzeigen
st.caption(f"Eingeloggt als: {user.get('email')} – Mandant: {hotel_id}")


# ---------------------------------------------------------
# RENDER-FUNKTIONEN
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

    render_rooms()
    render_free_rooms()


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
            st.rerun()


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
# HAUPTFUNKTION
# ---------------------------------------------------------
def main():
    init_state()

    with st.sidebar:
        st.title("Navigation")

        logout = st.button("Abmelden")

        st.markdown("---")

        st.session_state.show_rooms = st.checkbox(
            "Besetzte Räume anzeigen",
            value=st.session_state.get("show_rooms", False)
        )

        st.session_state.show_free_rooms = st.checkbox(
            "Freie Räume anzeigen",
            value=st.session_state.get("show_free_rooms", False)
        )

        st.markdown("---")

        pages = [
            "Dashboard",
            "Neuen Gast anlegen",
            "Gästeliste",
            "Gäste suchen",
            "Zimmerverwaltung",
            "Ausgecheckte Gäste",
        ]

        current_page = st.session_state.get("page", "Dashboard")
        if current_page not in pages:
            current_page = "Dashboard"

        st.session_state.page = st.radio(
            "Seite",
            pages,
            index=pages.index(current_page),
        )

    if logout:
        st.session_state.clear()
        st.rerun()

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
