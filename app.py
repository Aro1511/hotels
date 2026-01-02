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
from database import load_rooms
from models import Guest

from admin import admin_page


# ---------------------------------------------------------
# Grundkonfiguration
# ---------------------------------------------------------
st.set_page_config(page_title="Hotelverwaltung", layout="wide")


# ---------------------------------------------------------
# Logo anzeigen
# ---------------------------------------------------------
def image_to_base64(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

def show_logo_right():
    try:
        logo = Image.open("logo.png")
        encoded = image_to_base64(logo)

        st.markdown(
            f"""
            <div style="width: 100%; text-align: right; margin-top: 5px; margin-bottom: 5px;">
                <img src="data:image/png;base64,{encoded}" style="width: 180px;">
            </div>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        st.warning("Logo konnte nicht geladen werden.")

show_logo_right()


# ---------------------------------------------------------
# Hilfsfunktion: Beleg exportieren
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
# Seite: Neuer Gast
# ---------------------------------------------------------
def page_neuer_gast():
    st.header("Neuen Gast anlegen")

    if "form_hidden" not in st.session_state:
        st.session_state.form_hidden = False

    if st.session_state.form_hidden:
        st.success("Gast wurde erfolgreich gespeichert.")
        if st.button("Neuen Gast anlegen"):
            st.session_state.form_hidden = False
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

    if st.button("Gast speichern", key="save_guest"):
        if not name:
            st.error("Name darf nicht leer sein.")
        else:
            try:
                guest = add_guest(
                    "default_hotel",
                    name=name,
                    room_number=int(room_number),
                    room_category=room_category,
                    price_per_night=float(price_per_night),
                )
                st.session_state.form_hidden = True
                st.rerun()
            except Exception as e:
                st.error(str(e))


# ---------------------------------------------------------
# Gastdetails anzeigen
# ---------------------------------------------------------
def display_guest_details(guest: Guest, editable: bool = True):
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
                        set_night_paid_status("default_hotel", guest.id, n.number, False)
                        st.rerun()
                else:
                    if cols[2].button(
                        "Als bezahlt markieren",
                        key=f"paid_{guest.id}_{n.number}",
                    ):
                        set_night_paid_status("default_hotel", guest.id, n.number, True)
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
            add_unpaid = st.button("Unbezahlte Nacht hinzufügen", key=f"add_unpaid_{guest.id}")

        if add_paid:
            add_night_to_guest("default_hotel", guest.id, paid=True)
            st.rerun()

        if add_unpaid:
            add_night_to_guest("default_hotel", guest.id, paid=False)
            st.rerun()

        st.markdown("### Gast-Aktionen")
        if guest.status == "checked_in":
            if st.button("Checkout durchführen", key=f"checkout_{guest.id}"):
                checkout_guest("default_hotel", guest.id)
                st.success("Gast wurde ausgecheckt.")
                st.rerun()


# ---------------------------------------------------------
# Seite: Gästeliste
# ---------------------------------------------------------
def page_gaesteliste():
    st.header("Liste der Gäste")

    guests = list_all_guests("default_hotel", include_checked_out=False)

    if not guests:
        st.info("Keine Gäste vorhanden.")
        return

    for guest in guests:
        with st.expander(f"{guest.name} (ID: {guest.id})", expanded=False):
            display_guest_details(guest, editable=True)


# ---------------------------------------------------------
# Seite: Suche
# ---------------------------------------------------------
def page_suche():
    st.header("Gäste suchen")
    query = st.text_input("Name (oder Teil des Namens)", key="search_input")
    include_checked_out = st.checkbox("Auch ausgecheckte Gäste anzeigen", value=False, key="search_checkbox")

    if query:
        results = search_guests_by_name("default_hotel", query)

        if not include_checked_out:
            results = [g for g in results if g.status == "checked_in"]

        if not results:
            st.warning("Keine passenden Gäste gefunden.")
            return

        for guest in results:
            with st.expander(f"{guest.name} (ID: {guest.id})"):
                display_guest_details(guest, editable=True)


# ---------------------------------------------------------
# Seite: Zimmerverwaltung
# ---------------------------------------------------------
def page_zimmerverwaltung():
    st.header("Zimmerverwaltung")

    st.subheader("Neues Zimmer hinzufügen")
    col1, col2 = st.columns(2)
    with col1:
        number = st.number_input("Zimmernummer", min_value=1, step=1, key="room_number")
    with col2:
        category = st.selectbox(
            "Kategorie", ["Einzel", "Doppel", "Familie", "Suite", "Sonstige"], key="room_category"
        )

    if st.button("Zimmer speichern", key="save_room"):
        try:
            add_room("default_hotel", int(number), category)
            st.success(f"Zimmer {int(number)} hinzugefügt.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.subheader("Vorhandene Zimmer")
    rooms = load_rooms("default_hotel")

    if not rooms:
        st.info("Noch keine Zimmer vorhanden.")
    else:
        for r in rooms:
            st.write(
                f"Zimmer {r.number} – {r.category} – "
                f"{'Belegt' if r.occupied else 'Frei'}"
            )


# ---------------------------------------------------------
# Seite: Checkout
# ---------------------------------------------------------
def page_checkout():
    st.header("Ausgecheckte Gäste")

    guests = list_all_guests("default_hotel", include_checked_out=True)
    checked_out = [g for g in guests if g.status == "checked_out"]

    if not checked_out:
        st.info("Noch keine ausgecheckten Gäste.")
        return

    for guest in checked_out:
        with st.expander(f"{guest.name} (ID: {guest.id})"):
            display_guest_details(guest, editable=False)

            st.markdown("---")
            if st.button("Gast löschen", key=f"delete_{guest.id}"):
                delete_guest("default_hotel", guest.id)
                st.success("Gast wurde gelöscht.")
                st.rerun()


# ---------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------
def main():
    st.title("Hotelverwaltung – MVP")

    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Seite auswählen",
        ("Neuer Gast", "Gästeliste", "Suche", "Zimmerverwaltung", "Checkout", "Admin"),
        key="nav_radio"
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
    elif page == "Admin":
        admin_page()


if __name__ == "__main__":
    main()
