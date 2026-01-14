import streamlit as st
import csv
import io
from PIL import Image
import base64

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


# ---------------------------------------------------------
# CSS laden
# ---------------------------------------------------------
def load_css():
    try:
        with open("style.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except Exception:
        st.warning("Konnte style.css nicht laden.")


load_css()


# ---------------------------------------------------------
# Grundkonfiguration
# ---------------------------------------------------------
st.set_page_config(page_title="Hotelverwaltung", layout="wide")


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

if "auto_open_guest" not in st.session_state:
    st.session_state.auto_open_guest = None

if "guest_form_collapsed" not in st.session_state:
    st.session_state.guest_form_collapsed = False  # Formular standardmäßig offen


# ---------------------------------------------------------
# Logo laden
# ---------------------------------------------------------
def image_to_base64(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()


# ---------------------------------------------------------
# Moderner Header + Räume-Button
# ---------------------------------------------------------
def show_modern_header():
    try:
        logo = Image.open("logo.png")
        encoded = image_to_base64(logo)

        col1, col2 = st.columns([4, 1])

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
                        Hotelverwaltung
                    </h1>
                    <img src="data:image/png;base64,{encoded}" style="width: 140px;">
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            if st.button("Besitzte Räume"):
                st.session_state.show_rooms = not st.session_state.show_rooms

    except Exception:
        st.warning("Logo konnte nicht geladen werden.")


show_modern_header()


# ---------------------------------------------------------
# Räume anzeigen
# ---------------------------------------------------------
def render_rooms_overview():
    if not st.session_state.show_rooms:
        return

    rooms = load_rooms(hotel_id)

    st.markdown('<div class="card">', unsafe_allow_html=True)

    if not rooms:
        st.write("Keine Räume vorhanden.")
    else:
        st.write(f"Du besitzt **{len(rooms)} Räume**:")
        for r in rooms:
            st.write(f"• **Zimmer {r.number}** – {r.category}")

    st.markdown("</div>", unsafe_allow_html=True)


render_rooms_overview()


# ---------------------------------------------------------
# Beleg exportieren
# ---------------------------------------------------------
def export_receipt_csv(guest: Guest):
    paid_count, unpaid_count, sum_paid, sum_unpaid = calculate_nights_summary(guest)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow(["Beleg für Gast"])
    writer.writerow(["Name", guest.name])
    writer.writerow(["Zimmer", guest.room_number])
    writer.writerow(["Kategorie", guest.room_category])
    writer.writerow(["Preis pro Nacht", guest.price_per_night])
    writer.writerow(["Check-in", guest.checkin_date])
    writer.writerow(["Check-out", guest.checkout_date or "-"])
    writer.writerow([])
    writer.writerow(["Bezahlte Nächte", paid_count])
    writer.writerow(["Unbezahlte Nächte", unpaid_count])
    writer.writerow(["Summe bezahlt (€)", sum_paid])
    writer.writerow(["Summe offen (€)", sum_unpaid])
    writer.writerow([])
    writer.writerow(["Nacht", "Bezahlt"])

    for n in guest.nights:
        writer.writerow([n.number, "Ja" if n.paid else "Nein"])

    return output.getvalue()


# ---------------------------------------------------------
# Accordion: Gastdetails (ohne HTML-Tricks)
# ---------------------------------------------------------
def render_guest_accordion(guest: Guest, editable: bool = True):
    guest_id = guest.id
    is_open = st.session_state.open_guest_id == guest_id

    arrow = "▾" if is_open else "▸"
    label = f"{arrow} {guest.name}"

    # Button als Header
    if st.button(label, key=f"guest_header_{guest_id}"):
        if is_open:
            st.session_state.open_guest_id = None
        else:
            st.session_state.open_guest_id = guest_id
        st.rerun()

    # Inhalt nur anzeigen, wenn offen
    if is_open:
        display_guest_details(guest, editable)


# ---------------------------------------------------------
# Gastdetails anzeigen
# ---------------------------------------------------------
def display_guest_details(guest: Guest, editable: bool = True):
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.write(f"**Zimmer:** {guest.room_number} ({guest.room_category})")
    st.write(f"**Preis pro Nacht:** {guest.price_per_night:.2f} €")
    st.write(f"**Check-in:** {guest.checkin_date}")
    if guest.checkout_date:
        st.write(f"**Check-out:** {guest.checkout_date}")
    st.write(f"**Status:** {guest.status}")

    st.markdown("### Nächte")
    if not guest.nights:
        st.info("Noch keine Nächte eingetragen.")
    else:
        cols = st.columns([1, 2, 2])
        cols[0].markdown("**Nacht**")
        cols[1].markdown("**Bezahlt**")
        cols[2].markdown("**Aktion**")

        for n in guest.nights:
            cols = st.columns([1, 2, 2])
            cols[0].write(n.number)
            cols[1].write("Ja" if n.paid else "Nein")

            if editable:
                if n.paid:
                    if cols[2].button(
                        "Auf unbezahlte setzen",
                        key=f"unpaid_{guest.id}_{n.number}",
                    ):
                        set_night_paid_status(hotel_id, guest.id, n.number, False)
                        st.rerun()
                else:
                    if cols[2].button(
                        "Als bezahlt markieren",
                        key=f"paid_{guest.id}_{n.number}",
                    ):
                        set_night_paid_status(hotel_id, guest.id, n.number, True)
                        st.rerun()

    paid_count, unpaid_count, sum_paid, sum_unpaid = calculate_nights_summary(guest)
    st.markdown("### Zusammenfassung")
    st.write(f"**Bezahlte Nächte:** {paid_count} (Summe: {sum_paid:.2f} €)")
    st.write(f"**Unbezahlte Nächte:** {unpaid_count} (Summe: {sum_unpaid:.2f} €)")

    st.markdown("### Beleg exportieren")
    csv_data = export_receipt_csv(guest)
    st.download_button(
        label="Beleg als CSV herunterladen",
        data=csv_data,
        file_name=f"beleg_{guest.name.replace(' ', '_')}.csv",
        mime="text/csv",
        key=f"download_{guest.id}",
    )

    if editable:
        st.markdown("### Nächte hinzufügen")
        col_add1, col_add2 = st.columns(2)
        with col_add1:
            add_paid = st.button("Bezahlte Nacht hinzufügen", key=f"add_paid_{guest.id}")
        with col_add2:
            add_unpaid = st.button(
                "Unbezahlte Nacht hinzufügen", key=f"add_unpaid_{guest.id}"
            )

        if add_paid:
            add_night_to_guest(hotel_id, guest.id, paid=True)
            st.rerun()

        if add_unpaid:
            add_night_to_guest(hotel_id, guest.id, paid=False)
            st.rerun()

        st.markdown("### Gast-Aktionen")
        if guest.status == "checked_in":
            if st.button("Checkout durchführen", key=f"checkout_{guest.id}"):
                checkout_guest(hotel_id, guest.id)
                st.success("Gast wurde ausgecheckt.")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Seite: Neuer Gast
# ---------------------------------------------------------
def page_neuer_gast():
    st.header("Neuen Gast anlegen")

    # Formular nur einklappen, wenn gespeichert wurde
    if st.session_state.guest_form_collapsed:
        st.success("Gast wurde erfolgreich gespeichert.")
        if st.button("Neuen Gast anlegen"):
            st.session_state.guest_form_collapsed = False
            st.rerun()
        return

    name = st.text_input("Name des Gastes")

    col1, col2 = st.columns(2)
    with col1:
        room_number = st.number_input("Zimmernummer", min_value=1, step=1)
    with col2:
        room_category = st.selectbox(
            "Zimmerkategorie", ["Einzel", "Doppel", "Familie", "Suite", "Sonstige"]
        )

    price_per_night = st.number_input(
        "Preis pro Nacht (€)", min_value=0.0, step=1.0, format="%.2f"
    )

    if st.button("Gast speichern"):
        if not name:
            st.error("Name darf nicht leer sein.")
        else:
            new_guest = add_guest(
                hotel_id,
                name=name,
                room_number=int(room_number),
                room_category=room_category,
                price_per_night=float(price_per_night),
            )
            st.session_state.auto_open_guest = new_guest.id
            st.session_state.guest_form_collapsed = True
            st.rerun()


# ---------------------------------------------------------
# Seite: Gästeliste
# ---------------------------------------------------------
def page_gaesteliste():
    st.header("Liste der Gäste")

    guests = list_all_guests(hotel_id, include_checked_out=False)

    if not guests:
        st.info("Keine Gäste vorhanden.")
        return

    # Auto-Open nach Speichern
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

    query = st.text_input("Name (oder Teil des Namens)")
    include_checked_out = st.checkbox(
        "Auch ausgecheckte Gäste anzeigen", value=False
    )

    if query:
        results = search_guests_by_name(hotel_id, query)

        if not include_checked_out:
            results = [g for g in results if g.status == "checked_in"]

        if not results:
            st.warning("Keine passenden Gäste gefunden.")
            return

        for guest in results:
            render_guest_accordion(guest, editable=True)


# ---------------------------------------------------------
# Seite: Zimmerverwaltung
# ---------------------------------------------------------
def page_zimmerverwaltung():
    st.header("Zimmerverwaltung")

    st.subheader("Neues Zimmer hinzufügen")
    col1, col2 = st.columns(2)
    with col1:
        number = st.number_input("Zimmernummer", min_value=1, step=1)
    with col2:
        category = st.selectbox(
            "Kategorie",
            ["Einzel", "Doppel", "Familie", "Suite", "Sonstige"],
        )

    if st.button("Zimmer speichern"):
        try:
            add_room(hotel_id, int(number), category)
            st.success(f"Zimmer {int(number)} hinzugefügt.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.subheader("Vorhandene Zimmer")
    rooms = load_rooms(hotel_id)

    if not rooms:
        st.info("Noch keine Zimmer vorhanden.")
    else:
        for r in rooms:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write(f"**Zimmer:** {r.number}")
            st.write(f"**Kategorie:** {r.category}")
            st.write(f"**Status:** {'Belegt' if r.occupied else 'Frei'}")

            colA, colB = st.columns(2)

            with colA:
                if st.button("Raum löschen", key=f"delete_room_{r.number}"):
                    delete_room(hotel_id, r.number)
                    st.success("Raum gelöscht.")
                    st.rerun()

            with colB:
                if r.occupied:
                    if st.button("Raum freigeben", key=f"free_room_{r.number}"):
                        set_room_free(hotel_id, r.number)
                        st.success("Raum wurde freigegeben.")
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
        st.info("Noch keine ausgecheckten Gäste.")
        return

    for guest in checked_out:
        render_guest_accordion(guest, editable=False)

        if st.button("Gast löschen", key=f"delete_{guest.id}"):
            delete_guest(hotel_id, guest.id)
            st.success("Gast wurde gelöscht.")
            st.rerun()


# ---------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Seite auswählen",
        ("Neuer Gast", "Gästeliste", "Suche", "Zimmerverwaltung", "Checkout"),
    )

    if page == "Neuer Gast":
        page_neuer_gast()
    elif page == "Gästeliste":
        page_gaesteliste()
    elif page == "Suche":
        page_suche()
    elif page == "Zimmerverwaltung":
        page_zimmerverwaltung()
    elif page == "Checkout":
        page_checkout()


if __name__ == "__main__":
    main()
