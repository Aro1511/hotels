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
    update_guest_details,
)
from database import load_rooms, delete_room, set_room_free
from models import Guest
from utils import load_language, translator
from pdf_generator import generate_receipt_pdf, generate_receipt_csv
from users import change_password
from firebase_db import db


# ---------------------------------------------------------
# Session Defaults
# ---------------------------------------------------------
DEFAULTS = {
    "page": "Dashboard",
    "open_guest_id": None,
    "show_rooms": False,
    "show_free_rooms": False,
    "currency": "USD",
    "edit_guest_id": None,
}

def init_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ---------------------------------------------------------
# Helpers für Währung
# ---------------------------------------------------------
def get_currency_code():
    return st.session_state.get("currency", "USD")

def get_currency_symbol():
    code = get_currency_code()
    return {
        "EUR": "€",
        "USD": "$",
        "ETB": "Br",
        "SAR": "﷼",
        "GBP": "£",
        "CAD": "$",
    }.get(code, "$")


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
    symbol = get_currency_symbol()

    label = ("▾ " if is_open else "▸ ") + guest.name

    if st.button(label, key=f"guest_{gid}"):
        st.session_state["open_guest_id"] = None if is_open else gid
        st.rerun()

    if not is_open:
        return

    st.write(f"{t('guest_details_room')}: {guest.room_number} ({guest.room_category})")
    st.write(f"{t('guest_details_price')}: {guest.price_per_night} {symbol}")
    st.write(f"{t('checkin')}: {guest.checkin_date}")
    if guest.checkout_date:
        st.write(f"{t('checkout')}: {guest.checkout_date}")

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

    with st.expander(t("add_nights"), expanded=False):
        colA, colB = st.columns([1, 2])
        paid_new = colA.checkbox(t("paid"), key=f"paid_new_{gid}")
        label_btn = t("add_paid_night") if paid_new else t("add_unpaid_night")
        if colB.button(label_btn, key=f"add_night_{gid}"):
            add_night_to_guest(hotel_id, gid, paid_new)
            st.success(t("guest_saved"))
            st.rerun()

    st.write(f"### {t('summary')}")

    count_paid, count_unpaid, sum_paid, sum_unpaid = calculate_nights_summary(guest)

    st.write(f"{t('paid_nights')}: {count_paid}")
    st.write(f"{t('unpaid_nights')}: {count_unpaid}")
    st.write(f"{t('sum_paid')}: {sum_paid} {symbol}")
    st.write(f"{t('sum_unpaid')}: {sum_unpaid} {symbol}")
    st.write(f"**{t('total')}: {sum_paid + sum_unpaid} {symbol}**")

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

    st.write(f"### {t('guest_actions')}")

    if editable and guest.status == "checked_in":
        colA, colB = st.columns(2)
        if colA.button(t("checkout_guest"), key=f"checkout_{gid}"):
            checkout_guest(hotel_id, gid)
            st.success(t("guest_checked_out"))
            st.rerun()

        if colB.button(t("edit_guest"), key=f"edit_{gid}"):
            st.session_state["edit_guest_id"] = gid
            st.session_state["page"] = "Gast bearbeiten"
            st.rerun()

    if guest.status == "checked_out":
        if st.button(t("delete_guest_button"), key=f"delete_{gid}"):
            delete_guest(hotel_id, gid)
            st.success(t("guest_deleted"))
            st.rerun()


# ---------------------------------------------------------
# Dashboard
# ---------------------------------------------------------
def page_dashboard(hotel_id, t):
    st.header(t("dashboard"))

    symbol = get_currency_symbol()
    guests = list_all_guests(hotel_id, include_checked_out=True)
    rooms = load_rooms(hotel_id)

    current_guests = [g for g in guests if g.status == "checked_in"]
    checked_out_guests = [g for g in guests if g.status == "checked_out"]
    occupied_rooms = [r for r in rooms if r.occupied]
    free_rooms = [r for r in rooms if not r.occupied]

    now = datetime.now()
    current_year = now.year
    current_month = now.month

    revenue_this_month = 0.0
    unpaid_nights_this_month = 0
    unpaid_sum_this_month = 0.0

    monthly_stats = {}
    room_nights = {}
    open_balances = []

    for g in guests:
        cp, cu, sp, su = calculate_nights_summary(g)

        if g.room_number is not None:
            room_nights[g.room_number] = room_nights.get(g.room_number, 0) + (cp + cu)

        if cu > 0 and su > 0:
            open_balances.append((g, cu, su))

        if g.checkin_date:
            try:
                d = datetime.strptime(g.checkin_date, "%Y-%m-%d")
            except ValueError:
                continue

            key = (d.year, d.month)
            if key not in monthly_stats:
                monthly_stats[key] = [0, 0.0, 0]
            monthly_stats[key][0] += cp
            monthly_stats[key][1] += sp
            monthly_stats[key][2] += cu

            if d.year == current_year and d.month == current_month:
                revenue_this_month += sp
                unpaid_nights_this_month += cu
                unpaid_sum_this_month += su

    st.subheader(t("dashboard_summary_title"))
    st.write(f"{t('stats_current_guests')}: {len(current_guests)}")
    st.write(f"{t('stats_checked_out')}: {len(checked_out_guests)}")
    st.write(f"{t('stats_rooms_total')}: {len(rooms)}")
    st.write(f"{t('stats_rooms_occupied')}: {len(occupied_rooms)}")
    st.write(f"{t('stats_rooms_free')}: {len(free_rooms)}")
    st.write(f"{t('dashboard_revenue_this_month')}: {revenue_this_month} {symbol}")
    st.write(f"{t('dashboard_unpaid_nights_this_month')}: {unpaid_nights_this_month} ({unpaid_sum_this_month} {symbol})")

    st.markdown("---")

    st.subheader(t("dashboard_monthly_overview_title"))
    if not monthly_stats:
        st.info(t("dashboard_no_monthly_data"))
    else:
        rows = []
        for (y, m), (paid_n, rev, unpaid_n) in sorted(monthly_stats.items()):
            rows.append({
                t("dashboard_table_year"): y,
                t("dashboard_table_month"): m,
                t("dashboard_table_paid_nights"): paid_n,
                t("dashboard_table_revenue"): f"{rev} {symbol}",
                t("dashboard_table_unpaid_nights"): unpaid_n,
            })
        st.table(rows)

    st.markdown("---")

    st.subheader(t("dashboard_top_rooms_title"))
    if not room_nights:
        st.info(t("dashboard_no_top_rooms"))
    else:
        sorted_rooms = sorted(room_nights.items(), key=lambda x: x[1], reverse=True)[:10]
        rows = []
        for room_number, nights in sorted_rooms:
            rows.append({
                t("room"): room_number,
                t("dashboard_room_nights"): nights,
            })
        st.table(rows)

    # ⭐ KORREKTUR HIER:
    st.markdown("---")

    st.subheader(t("dashboard_open_balances_title"))
    if not open_balances:
        st.info(t("dashboard_no_open_balances"))
    else:
        rows = []
        for g, cu, su in open_balances:
            rows.append({
                t("guest_name_label"): g.name,
                t("room_number_label"): g.room_number,
                t("unpaid_nights"): cu,
                t("sum_unpaid"): f"{su} {symbol}",
            })
        st.table(rows)
# ---------------------------------------------------------
# Neue Gäste anlegen
# ---------------------------------------------------------
def page_new_guest(hotel_id, t):
    st.header(t("new_guest_page"))

    with st.expander(t("create_new_guest"), expanded=False):
        name = st.text_input(t("guest_name_label"))
        room = st.number_input(t("room_number_label"), min_value=1)

        category_options = [
            t("room_cat_single"),
            t("room_cat_double"),
            t("room_cat_family"),
            t("room_cat_suite"),
        ]
        category = st.selectbox(t("room_category_label"), category_options)

        price = st.number_input(t("price_per_night_label"), min_value=0.0)

        if st.button(t("save_guest")):
            if not name:
                st.error(t("name_required"))
            else:
                add_guest(hotel_id, name, int(room), category, float(price))
                st.success(t("guest_saved"))
                st.rerun()


# ---------------------------------------------------------
# Gästeliste
# ---------------------------------------------------------
def page_guest_list(hotel_id, t):
    st.header(t("guest_list_page"))

    guests = list_all_guests(hotel_id, include_checked_out=False)

    if not guests:
        st.info(t("no_guests"))
        return

    for g in guests:
        render_guest_accordion(hotel_id, g, t)


# ---------------------------------------------------------
# Suche
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# Zimmerverwaltung
# ---------------------------------------------------------
def page_rooms(hotel_id, t):
    st.header(t("room_management_page"))

    with st.expander(t("add_room_section"), expanded=False):
        number = st.number_input(t("room_number"), min_value=1, key="room_number_input")

        category_options = [
            t("room_cat_single"),
            t("room_cat_double"),
            t("room_cat_family"),
            t("room_cat_suite"),
        ]
        category = st.selectbox(t("room_category"), category_options, key="room_category_input")

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


# ---------------------------------------------------------
# Checkout
# ---------------------------------------------------------
def page_checkout(hotel_id, t):
    st.header(t("checkout_page"))

    guests = list_all_guests(hotel_id, include_checked_out=True)
    checked_out = [g for g in guests if g.status == "checked_out"]

    if not checked_out:
        st.info(t("no_checked_out_guests"))
        return

    for g in checked_out:
        render_guest_accordion(hotel_id, g, t, editable=False)


# ---------------------------------------------------------
# Monatsbericht
# ---------------------------------------------------------
def page_monthly_report(hotel_id, t):
    st.header(t("monthly_report"))

    guests = list_all_guests(hotel_id, include_checked_out=True)
    symbol = get_currency_symbol()

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
    year = col1.selectbox(t("year"), years, index=len(years) - 1)
    month = col2.selectbox(t("month"), list(range(1, 13)), index=now.month - 1)

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
        st.info(t("no_month_data"))
        return

    st.subheader(t("monthly_details"))
    for g, cp, cu, sp, su in filtered:
        st.write(f"**{g.name}** – {t('room')} {g.room_number}")
        st.write(f"{t('paid_nights')}: {cp}, {t('unpaid_nights')}: {cu}")
        st.write(f"{t('sum_paid')}: {sp} {symbol}, {t('sum_unpaid')}: {su} {symbol}")
        st.markdown("---")

    st.subheader(t("monthly_total"))
    st.write(f"{t('sum_paid')}: {total_paid} {symbol}")
    st.write(f"{t('sum_unpaid')}: {total_unpaid} {symbol}")
    st.write(f"{t('total')}: {total_paid + total_unpaid} {symbol}")
# ---------------------------------------------------------
# Gast bearbeiten
# ---------------------------------------------------------
def page_edit_guest(hotel_id, t):
    gid = st.session_state.get("edit_guest_id")
    if not gid:
        st.error("Kein Gast ausgewählt.")
        return

    guests = list_all_guests(hotel_id, include_checked_out=True)
    guest = next((g for g in guests if g.id == gid), None)

    if not guest:
        st.error("Gast nicht gefunden.")
        return

    st.header(t("edit_guest"))

    # Zimmernummer
    room_number = st.number_input(
        t("room_number_label"),
        min_value=1,
        value=guest.room_number,
        key=f"edit_room_{gid}"
    )

    # Zimmerkategorie
    category_options = [
        t("room_cat_single"),
        t("room_cat_double"),
        t("room_cat_family"),
        t("room_cat_suite"),
    ]

    try:
        idx = category_options.index(guest.room_category)
    except ValueError:
        idx = 0

    room_category = st.selectbox(
        t("room_category_label"),
        category_options,
        index=idx,
        key=f"edit_cat_{gid}"
    )

    # Preis
    price = st.number_input(
        t("price_per_night_label"),
        min_value=0.0,
        value=float(guest.price_per_night),
        key=f"edit_price_{gid}"
    )

    # Speichern
    if st.button(t("save_changes"), key=f"save_changes_{gid}"):
        try:
            update_guest_details(
                hotel_id,
                guest_id=gid,
                new_room_number=int(room_number),
                new_room_category=room_category,
                new_price=float(price),
            )
            st.success(t("guest_updated"))

            st.session_state["edit_guest_id"] = None
            st.session_state["page"] = "Gästeliste"
            st.rerun()

        except ValueError as e:
            st.error(str(e))


# ---------------------------------------------------------
# Sidebar Navigation (KORRIGIERT!)
# ---------------------------------------------------------
def render_sidebar(t, user):
    with st.sidebar:
        st.title(t("navigation"))

        logout = st.button(t("logout"))

        st.markdown("---")

        # Zimmerfilter
        st.session_state["show_rooms"] = st.checkbox(
            t("stats_rooms_occupied"),
            value=st.session_state.get("show_rooms", False),
        )

        st.session_state["show_free_rooms"] = st.checkbox(
            t("stats_rooms_free"),
            value=st.session_state.get("show_free_rooms", False),
        )

        st.markdown("---")

        # Währung
        currency_options = {
            "USD": t("currency_usd"),
            "EUR": t("currency_eur"),
            "ETB": t("currency_etb"),
            "SAR": t("currency_sar"),
            "GBP": t("currency_gbp"),
            "CAD": t("currency_cad"),
        }

        current_code = st.session_state.get("currency", "USD")
        current_label = currency_options[current_code]

        selected_label = st.selectbox(
            t("currency"),
            list(currency_options.values()),
            index=list(currency_options.values()).index(current_label),
        )

        reverse_map = {v: k for k, v in currency_options.items()}
        new_code = reverse_map[selected_label]

        if new_code != current_code:
            st.session_state["currency"] = new_code
            try:
                db.collection("users").document(user["id"]).update({"currency": new_code})
                st.session_state["user"]["currency"] = new_code
            except Exception:
                pass

        st.markdown("---")

        # Seiten (OHNE „Gast bearbeiten“)
        pages = {
            t("dashboard"): "Dashboard",
            t("new_guest_page"): "Neuen Gast anlegen",
            t("guest_list_page"): "Gästeliste",
            t("search_page"): "Suche",
            t("room_management_page"): "Zimmerverwaltung",
            t("checkout_page"): "Checkout",
            t("monthly_report"): "Monatsabrechnung",
            t("change_password"): "Passwort ändern",
        }

        labels = list(pages.keys())
        values = list(pages.values())

        # aktuelle Seite aus Session State
        current_page = st.session_state.get("page", "Dashboard")

        # passenden Index finden
        try:
            current_index = values.index(current_page)
        except ValueError:
            current_index = 0

        selected_label_page = st.radio(
            t("select_page"),
            labels,
            index=current_index
        )

        st.session_state["page"] = pages[selected_label_page]

        return logout


# ---------------------------------------------------------
# Passwort ändern
# ---------------------------------------------------------
def page_change_password(hotel_id, t):
    st.header(t("change_password"))

    with st.expander(t("change_password"), expanded=False):
        old_pw = st.text_input(t("old_password"), type="password")
        new_pw = st.text_input(t("new_password"), type="password")
        new_pw2 = st.text_input(t("confirm_password"), type="password")

        if st.button(t("save_password")):
            if new_pw != new_pw2:
                st.error(t("passwords_not_match"))
                return

            try:
                change_password(st.session_state["user"]["email"], old_pw, new_pw)
                st.success(t("password_changed"))
            except Exception as e:
                st.error(str(e))


# ---------------------------------------------------------
# Routing + MAIN
# ---------------------------------------------------------
def main():
    # Benutzer muss eingeloggt sein
    if "user" not in st.session_state or not st.session_state["user"]:
        st.write("Bitte zuerst einloggen…")
        st.stop()

    user = st.session_state["user"]
    hotel_id = user.get("tenant_id")

    # Sprache laden
    lang = st.session_state.get("language", "de")
    texts = load_language(lang)
    t = translator(texts)

    # Währung initialisieren
    if "currency" not in st.session_state:
        user_currency = user.get("currency", "USD")
        st.session_state["currency"] = user_currency

    # Streamlit Setup
    st.set_page_config(page_title=t("app_title"), layout="wide")
    load_css()
    init_state()

    # Header
    show_header(t)
    st.caption(f"Eingeloggt als: {user.get('email')} – Mandant: {hotel_id}")

    # Sidebar rendern
    logout = render_sidebar(t, user)

    # Logout
    if logout:
        lang = st.session_state.get("language", "de")
        st.session_state.clear()
        st.session_state["language"] = lang
        st.rerun()

    # Routing
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

    elif page == "Passwort ändern":
        page_change_password(hotel_id, t)

    elif page == "Gast bearbeiten":
        page_edit_guest(hotel_id, t)


# ---------------------------------------------------------
# Startpunkt
# ---------------------------------------------------------
if __name__ == "__main__":
    main()
