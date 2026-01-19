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
                        {t("header_title")}
                    </h1>
                    <img src="data:image/png;base64,{encoded}" style="width: 140px;">
                </div>
                """,
                unsafe_allow_html=True,
            )

        with col2:
            if st.button(t("owned_rooms_button")):
                st.session_state.show_rooms = not st.session_state.show_rooms

    except Exception:
        pass


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
        st.write(t("no_rooms"))
    else:
        st.write(t("you_have_rooms").replace("{count}", str(len(rooms))))
        for r in rooms:
            st.write(
                "• " + t("room_item")
                .replace("{number}", str(r.number))
                .replace("{category}", r.category)
            )

    st.markdown("</div>", unsafe_allow_html=True)


render_rooms_overview()


# ---------------------------------------------------------
# CSV Export
# ---------------------------------------------------------
def export_receipt_csv(guest: Guest):
    paid_count, unpaid_count, sum_paid, sum_unpaid = calculate_nights_summary(guest)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([t("receipt_for_guest")])
    writer.writerow([t("guest_name"), guest.name])
    writer.writerow([t("room"), guest.room_number])
    writer.writerow([t("category"), guest.room_category])
    writer.writerow([t("price_per_night"), guest.price_per_night])
    writer.writerow([t("checkin"), guest.checkin_date])
    writer.writerow([t("checkout"), guest.checkout_date or "-"])
    writer.writerow([])
    writer.writerow([t("paid_nights"), paid_count])
    writer.writerow([t("unpaid_nights"), unpaid_count])
    writer.writerow([t("sum_paid"), sum_paid])
    writer.writerow([t("sum_unpaid"), sum_unpaid])
    writer.writerow([])
    writer.writerow([t("night"), t("paid")])

    for n in guest.nights:
        writer.writerow([n.number, t("yes") if n.paid else t("no")])

    return output.getvalue()


# ---------------------------------------------------------
# Accordion: Gastdetails
# ---------------------------------------------------------
def render_guest_accordion(guest: Guest, editable: bool = True):
    guest_id = guest.id
    is_open = st.session_state.open_guest_id == guest_id

    arrow = "▾" if is_open else "▸"
    label = f"{arrow} {guest.name}"

    if st.button(label, key=f"guest_header_{guest_id}"):
        if is_open:
            st.session_state.open_guest_id = None
        else:
            st.session_state.open_guest_id = guest_id
        st.rerun()

    if is_open:
        display_guest_details(guest, editable)


# ---------------------------------------------------------
# Gastdetails anzeigen
# ---------------------------------------------------------
def display_guest_details(guest: Guest, editable: bool = True):
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.write(f"**{t('guest_details_room')}:** {guest.room_number} ({guest.room_category})")
    st.write(f"**{t('guest_details_price')}:** {guest.price_per_night:.2f} €")
    st.write(f"**{t('checkin')}:** {guest.checkin_date}")
    if guest.checkout_date:
        st.write(f"**{t('checkout')}:** {guest.checkout_date}")
    st.write(f"**{t('guest_details_status')}:** {guest.status}")

    st.markdown(f"### {t('guest_details_nights')}")
    if not guest.nights:
        st.info(t("no_nights"))
    else:
        cols = st.columns([1, 2, 2])
        cols[0].markdown(f"**{t('night')}**")
        cols[1].markdown(f"**{t('paid')}**")
        cols[2].markdown(f"**{t('action')}**")

        for n in guest.nights:
            cols = st.columns([1, 2, 2])
            cols[0].write(n.number)
            cols[1].write(t("yes") if n.paid else t("no"))

            if editable:
                if n.paid:
                    if cols[2].button(
                        t("set_unpaid"),
                        key=f"unpaid_{guest.id}_{n.number}",
                    ):
                        set_night_paid_status(hotel_id, guest.id, n.number, False)
                        st.rerun()
                else:
                    if cols[2].button(
                        t("set_paid"),
                        key=f"paid_{guest.id}_{n.number}",
                    ):
                        set_night_paid_status(hotel_id, guest.id, n.number, True)
                        st.rerun()

    paid_count, unpaid_count, sum_paid, sum_unpaid = calculate_nights_summary(guest)
    st.markdown(f"### {t('summary')}")
    st.write(
        f"**{t('paid_nights')}:** {paid_count} (Summe: {sum_paid:.2f} €)"
    )
    st.write(
        f"**{t('unpaid_nights')}:** {unpaid_count} (Summe: {sum_unpaid:.2f} €)"
    )

    st.markdown(f"### {t('export_receipt')}")
    csv_data = export_receipt_csv(guest)
    st.download_button(
        label=t("download_receipt_csv"),
        data=csv_data,
        file_name=f"beleg_{guest.name.replace(' ', '_')}.csv",
        mime="text/csv",
        key=f"download_{guest.id}",
    )

    # PDF Export
    pdf_data = generate_receipt_pdf(guest, t)
    st.download_button(
        label=t("download_receipt_pdf"),
        data=pdf_data,
        file_name=f"beleg_{guest.name.replace(' ', '_')}.pdf",
        mime="application/pdf",
        key=f"pdf_{guest.id}",
    )

    if editable:
        st.markdown(f"### {t('add_nights')}")
        col_add1, col_add2 = st.columns(2)
        with col_add1:
            add_paid = st.button(
                t("add_paid_night"), key=f"add_paid_{guest.id}"
            )
        with col_add2:
            add_unpaid = st.button(
                t("add_unpaid_night"), key=f"add_unpaid_{guest.id}"
            )

        if add_paid:
            add_night_to_guest(hotel_id, guest.id, paid=True)
            st.rerun()

        if add_unpaid:
            add_night_to_guest(hotel_id, guest.id, paid=False)
            st.rerun()

        st.markdown(f"### {t('guest_actions')}")
        if guest.status == "checked_in":
            if st.button(t("checkout_guest"), key=f"checkout_{guest.id}"):
                checkout_guest(hotel_id, guest.id)
                st.success(t("guest_checked_out"))
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Seite: Neuer Gast
# ---------------------------------------------------------
def page_neuer_gast():
    st.header(t("new_guest_page"))

    if st.session_state.guest_form_collapsed:
        st.success(t("guest_saved"))
        if st.button(t("create_new_guest")):
            st.session_state.guest_form_collapsed = False
            st.rerun()
        return

    name = st.text_input(t("guest_name_label"))

    col1, col2 = st.columns(2)
    with col1:
        room_number = st.number_input(t("room_number_label"), min_value=1, step=1)
    with col2:
        room_category = st.selectbox(
            t("room_category_label"),
            ["Einzel", "Doppel", "Familie", "Suite", "Sonstige"],
        )

    price_per_night = st.number_input(
        t("price_per_night_label"), min_value=0.0, step=1.0, format="%.2f"
    )

    if st.button(t("save_guest")):
        if not name:
            st.error(t("name_required"))
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
    st.header(t("guest_list_page"))

    guests = list_all_guests(hotel_id, include_checked_out=False)

    if not guests:
        st.info(t("no_guests"))
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
    st.header(t("search_page"))

    query = st.text_input(t("search_name"))
    include_checked_out = st.checkbox(
        t("include_checked_out"), value=False
    )

    if query:
        results = search_guests_by_name(hotel_id, query)

        if not include_checked_out:
            results = [g for g in results if g.status == "checked_in"]

        if not results:
            st.warning(t("no_results"))
            return

        for guest in results:
            render_guest_accordion(guest, editable=True)


# ---------------------------------------------------------
# Seite: Zimmerverwaltung
# ---------------------------------------------------------
def page_zimmerverwaltung():
    st.header(t("room_management_page"))

    st.subheader(t("add_room_section"))
    col1, col2 = st.columns(2)
    with col1:
        number = st.number_input(t("room_number"), min_value=1, step=1)
    with col2:
        category = st.selectbox(
            t("room_category"),
            ["Einzel", "Doppel", "Familie", "Suite", "Sonstige"],
        )

    if st.button(t("save_room")):
        try:
            add_room(hotel_id, int(number), category)
            st.success(
                t("room_added").replace("{number}", str(int(number)))
            )
            st.rerun()
        except Exception as e:
            st.error(str(e))

    st.subheader(t("existing_rooms"))
    rooms = load_rooms(hotel_id)

    if not rooms:
        st.info(t("no_rooms_yet"))
    else:
        for r in rooms:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write(f"**{t('room')}:** {r.number}")
            st.write(f"**{t('room_category')}:** {r.category}")
            st.write(
                f"**{t('room_status')}:** "
                f"{t('occupied') if r.occupied else t('free')}"
            )

            colA, colB = st.columns(2)

            with colA:
                if st.button(t("delete_room"), key=f"delete_room_{r.number}"):
                    delete_room(hotel_id, r.number)
                    st.success(t("room_deleted"))
                    st.rerun()

            with colB:
                if r.occupied:
                    if st.button(t("free_room"), key=f"free_room_{r.number}"):
                        set_room_free(hotel_id, r.number)
                        st.success(t("room_freed"))
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------
# Seite: Checkout
# ---------------------------------------------------------
def page_checkout():
    st.header(t("checkout_page"))

    guests = list_all_guests(hotel_id, include_checked_out=True)
    checked_out = [g for g in guests if g.status == "checked_out"]

    if not checked_out:
        st.info(t("no_checked_out_guests"))
        return

    for guest in checked_out:
        render_guest_accordion(guest, editable=False)

        if st.button(t("delete_guest_button"), key=f"delete_{guest.id}"):
            delete_guest(hotel_id, guest.id)
            st.success(t("guest_deleted"))
            st.rerun()


# ---------------------------------------------------------
# Hauptprogramm
# ---------------------------------------------------------
def main():
    with st.sidebar:
        st.title(t("navigation"))

        current_lang = st.session_state.get("language", "de")
        lang_options = {
            t("german"): "de",
            t("english"): "en"
        }
        selected_label = st.radio(
            t("language"),
            list(lang_options.keys()),
            index=0 if current_lang == "de" else 1
        )
        new_lang = lang_options[selected_label]
        if new_lang != current_lang:
            st.session_state["language"] = new_lang
            st.rerun()

        st.markdown("---")

        page = st.radio(
            t("select_page"),
            (
                t("page_new_guest"),
                t("page_guest_list"),
                t("page_search"),
                t("page_room_management"),
                t("page_checkout"),
            ),
        )

    if page == t("page_new_guest"):
        page_neuer_gast()
    elif page == t("page_guest_list"):
        page_gaesteliste()
    elif page == t("page_search"):
        page_suche()
    elif page == t("page_room_management"):
        page_zimmerverwaltung()
    elif page == t("page_checkout"):
        page_checkout()


if __name__ == "__main__":
    main()
