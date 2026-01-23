import streamlit as st
import io
import base64
from PIL import Image
from datetime import datetime

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
from pdf_generator import generate_receipt_pdf, generate_receipt_csv


# ---------------------------------------------------------
# Session Defaults
# ---------------------------------------------------------
DEFAULTS = {
    "page": "Dashboard",
    "open_guest_id": None,
    "show_rooms": False,
    "show_free_rooms": False,
}

def init_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
# Header
# ---------------------------------------------------------
def image_to_base64(img):
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode()

def show_header(t):
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


# ---------------------------------------------------------
# Guest Accordion
# ---------------------------------------------------------
def render_guest_accordion(hotel_id: str, guest: Guest, t, editable=True):
    gid = guest.id
    is_open = st.session_state.get("open_guest_id") == gid

    label = ("▾ " if is_open else "▸ ") + guest.name

    if st.button(label, key=f"guest_{gid}"):
        st.session_state["open_guest_id"] = None if is_open else gid
        st.rerun()

    if not is_open:
        return

    st.write(f"{t('guest_details_room')}: {guest.room_number} ({guest.room_category})")
    st.write(f"{t('guest_details_price')}: {guest.price_per_night} €")
    st.write(f"{t('checkin')}: {guest.checkin_date}")
    if guest.checkout_date:
        st.write(f"{t('checkout')}: {guest.checkout_date}")

    # Nächte
    st.write(f"### {t('guest_details_nights')}")

    if not guest.nights:
        st.info(t("no_nights"))

    for n in guest.nights:
        col1, col2, col3 = st.columns([1, 1, 2])
        col1.write(f"{t('night')} {n.number}")
        col2.write(t("yes") if n.paid else t("no"))

        if editable:
            if n.paid:
                if col3.button(t("set_unpaid"), key=f"unpaid_{gid}_{n.number}"):
                    set_night_paid_status(hotel_id, gid, n.number, False)
                    st.rerun()
            else:
                if col3.button(t("set_paid"), key=f"paid_{gid}_{n.number}"):
                    set_night_paid_status(hotel_id, gid, n.number, True)
                    st.rerun()

    # Neue Nacht hinzufügen (Formular im Expander)
    with st.expander(t("add_nights"), expanded=False):
        colA, colB = st.columns([1, 2])
        paid_new = colA.checkbox(t("paid"), key=f"paid_new_{gid}")
        label_btn = t("add_paid_night") if paid_new else t("add_unpaid_night")
        if colB.button(label_btn, key=f"add_night_{gid}"):
            add_night_to_guest(hotel_id, gid, paid_new)
            st.success(t("guest_saved"))
            st.rerun()

    # Preisübersicht
    st.write(f"### {t('summary')}")

    count_paid, count_unpaid, sum_paid, sum_unpaid = calculate_nights_summary(guest)

    st.write(f"{t('paid_nights')}: {count_paid}")
    st.write(f"{t('unpaid_nights')}: {count_unpaid}")
    st.write(f"{t('sum_paid')}: {sum_paid} €")
    st.write(f"{t('sum_unpaid')}: {sum_unpaid} €")
    st.write(f"**Gesamt: {sum_paid + sum_unpaid} €**")

    # PDF & CSV
    pdf_bytes = generate_receipt_pdf(guest, t)
    st.download_button(
        t("download_receipt_pdf"),
        data=pdf_bytes,
        file_name=f"Beleg_{guest.name}.pdf",
        mime="application/pdf",
        key=f"pdf_{gid}",
    )

    csv_bytes = generate_receipt_csv(guest, t)
    st.download_button(
        t("download_receipt_csv"),
        data=csv_bytes,
        file_name=f"Beleg_{guest.name}.csv",
        mime="text/csv",
        key=f"csv_{gid}",
    )

    # Aktionen
    st.write(f"### {t('guest_actions')}")

    if editable and guest.status == "checked_in":
        if st.button(t("checkout_guest"), key=f"checkout_{gid}"):
            checkout_guest(hotel_id, gid)
            st.success(t("guest_checked_out"))
            st.rerun()

    if guest.status == "checked_out":
        if st.button(t("delete_guest_button"), key=f"delete_{gid}"):
            delete_guest(hotel_id, gid)
            st.success(t("guest_deleted"))
            st.rerun()


# ---------------------------------------------------------
# Pages
# ---------------------------------------------------------
def page_dashboard(hotel_id, t):
    st.header(t("dashboard"))

    guests = list_all_guests(hotel_id, include_checked_out=True)
    rooms = load_rooms(hotel_id)

    st.write(f"{t('stats_current_guests')}: {len([g for g in guests if g.status=='checked_in'])}")
    st.write(f"{t('stats_checked_out')}: {len([g for g in guests if g.status=='checked_out'])}")
    st.write(f"{t('stats_rooms_total')}: {len(rooms)}")

    if st.session_state.get("show_rooms"):
        st.subheader(t("stats_rooms_occupied"))
        for r in rooms:
            if r.occupied:
                st.write(f"• {t('room')} {r.number} ({r.category})")

    if st.session_state.get("show_free_rooms"):
        st.subheader(t("stats_rooms_free"))
        for r in rooms:
            if not r.occupied:
                st.write(f"• {t('room')} {r.number} ({r.category})")


def page_new_guest(hotel_id, t):
    st.header(t("new_guest_page"))

    with st.expander(t("create_new_guest"), expanded=False):
        name = st.text_input(t("guest_name_label"))
        room = st.number_input(t("room_number_label"), min_value=1)
        category = st.selectbox(t("room_category_label"), ["Einzel", "Doppel", "Familie", "Suite"])
        price = st.number_input(t("price_per_night_label"), min_value=0.0)

        if st.button(t("save_guest")):
            if not name:
                st.error(t("name_required"))
            else:
                add_guest(hotel_id, name, int(room), category, float(price))
                st.success(t("guest_saved"))
                st.rerun()


def page_guest_list(hotel_id, t):
    st.header(t("guest_list_page"))

    guests = list_all_guests(hotel_id, include_checked_out=False)

    if not guests:
        st.info(t("no_guests"))
        return

    for g in guests:
        render_guest_accordion(hotel_id, g, t)


def page_search(hotel_id, t):
    st.header(t("search_page"))

    q = ""
    with st.expander(t("search_page"), expanded=False):
        q = st.text_input(t("search_name"))

    if q:
        results = search_guests_by_name(hotel_id, q)
        if not results:
            st.warning(t("no_results"))
        else:
            for g in results:
                render_guest_accordion(hotel_id, g, t)


def page_rooms(hotel_id, t):
    st.header(t("room_management_page"))

    # Neues Zimmer hinzufügen (Formular im Expander)
    with st.expander(t("add_room_section"), expanded=False):
        number = st.number_input(t("room_number"), min_value=1, key="room_number_input")
        category = st.selectbox(t("room_category"), ["Einzel", "Doppel", "Familie", "Suite"], key="room_category_input")

        if st.button(t("save_room"), key="save_room_btn"):
            add_room(hotel_id, int(number), category)
            st.success(t("room_added").format(number=number))
            st.rerun()

    st.subheader(t("existing_rooms"))
    rooms = load_rooms(hotel_id)

    if not rooms:
        st.info(t("no_rooms_yet"))
        return

    for r in rooms:
        col1, col2, col3 = st.columns([3, 1, 1])
        col1.write(f"{t('room')} {r.number} – {r.category} – {t('occupied') if r.occupied else t('free')}")

        if col2.button(t("delete_room"), key=f"del_room_{r.number}"):
            delete_room(hotel_id, r.number)
            st.success(t("room_deleted"))
            st.rerun()

        if r.occupied and col3.button(t("free_room"), key=f"free_room_{r.number}"):
            set_room_free(hotel_id, r.number)
            st.success(t("room_freed"))
            st.rerun()


def page_checkout(hotel_id, t):
    st.header(t("checkout_page"))

    guests = list_all_guests(hotel_id, include_checked_out=True)
    checked_out = [g for g in guests if g.status == "checked_out"]

    if not checked_out:
        st.info(t("no_checked_out_guests"))
        return

    for g in checked_out:
        render_guest_accordion(hotel_id, g, t, editable=False)


def page_monthly_report(hotel_id, t):
    st.header("Monatsabrechnung")

    guests = list_all_guests(hotel_id, include_checked_out=True)

    now = datetime.now()
    years = {now.year}
    for g in guests:
        if g.checkin_date:
            try:
                d = datetime.strptime(g.checkin_date, "%Y-%m-%d")
                years.add(d.year)
            except ValueError:
                pass
    years = sorted(years)

    col1, col2 = st.columns(2)
    year = col1.selectbox("Jahr", years, index=len(years) - 1)
    month = col2.selectbox("Monat", list(range(1, 13)), index=now.month - 1)

    filtered = []
    total_paid = 0.0
    total_unpaid = 0.0

    for g in guests:
        if not g.checkin_date:
            continue
        try:
            d = datetime.strptime(g.checkin_date, "%Y-%m-%d")
        except ValueError:
            continue
        if d.year == year and d.month == month:
            cp, cu, sp, su = calculate_nights_summary(g)
            filtered.append((g, cp, cu, sp, su))
            total_paid += sp
            total_unpaid += su

    if not filtered:
        st.info("Keine Daten für diesen Monat.")
        return

    st.subheader("Details pro Gast")
    for g, cp, cu, sp, su in filtered:
        st.write(f"**{g.name}** – Zimmer {g.room_number}")
        st.write(f"{t('paid_nights')}: {cp}, {t('unpaid_nights')}: {cu}")
        st.write(f"{t('sum_paid')}: {sp} €, {t('sum_unpaid')}: {su} €")
        st.markdown("---")

    st.subheader("Gesamtsumme")
    st.write(f"{t('sum_paid')}: {total_paid} €")
    st.write(f"{t('sum_unpaid')}: {total_unpaid} €")
    st.write(f"Gesamt: {total_paid + total_unpaid} €")


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
def main():
    if "user" not in st.session_state or not st.session_state["user"]:
        st.write("Bitte zuerst einloggen…")
        st.stop()

    user = st.session_state["user"]
    hotel_id = user.get("tenant_id")

    lang = st.session_state.get("language", "de")
    texts = load_language(lang)
    t = translator(texts)

    st.set_page_config(page_title=t("app_title"), layout="wide")
    load_css()
    init_state()

    show_header(t)
    st.caption(f"Eingeloggt als: {user.get('email')} – Mandant: {hotel_id}")

    # Sidebar
    with st.sidebar:
        st.title(t("navigation"))

        logout = st.button("Abmelden")

        st.markdown("---")

        st.session_state["show_rooms"] = st.checkbox(
            t("stats_rooms_occupied"),
            value=st.session_state.get("show_rooms", False),
        )

        st.session_state["show_free_rooms"] = st.checkbox(
            t("stats_rooms_free"),
            value=st.session_state.get("show_free_rooms", False),
        )

        st.markdown("---")

        pages = {
            t("dashboard"): "Dashboard",
            t("new_guest_page"): "Neuen Gast anlegen",
            t("guest_list_page"): "Gästeliste",
            t("search_page"): "Suche",
            t("room_management_page"): "Zimmerverwaltung",
            t("checkout_page"): "Checkout",
            "Monatsabrechnung": "Monatsabrechnung",
        }

        selected_label = st.radio(t("select_page"), list(pages.keys()))
        st.session_state["page"] = pages[selected_label]

    if logout:
        lang = st.session_state.get("language", "de")
        st.session_state.clear()
        st.session_state["language"] = lang
        st.rerun()

    page = st.session_state["page"]

    if page == "Dashboard":
        page_dashboard(hotel_id, t)
    elif page == "Neuen Gast anlegen":
        page_new_guest(hotel_id, t)
    elif page == "Gästeliste":
        page_guest_list(hotel_id, t)
    elif page == "Suche":
        page_search(hotel_id, t)
    elif page == "Zimmerverwaltung":
        page_rooms(hotel_id, t)
    elif page == "Checkout":
        page_checkout(hotel_id, t)
    elif page == "Monatsabrechnung":
        page_monthly_report(hotel_id, t)


if __name__ == "__main__":
    main()
