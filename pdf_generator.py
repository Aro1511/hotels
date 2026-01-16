import requests
from fpdf import FPDF
from datetime import datetime
from models import Guest
import os


FONT_URL = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
FONT_FILE = "DejaVuSans.ttf"


def ensure_font_exists():
    if not os.path.exists(FONT_FILE):
        r = requests.get(FONT_URL)
        with open(FONT_FILE, "wb") as f:
            f.write(r.content)


def generate_receipt_pdf(guest: Guest, t):
    ensure_font_exists()

    pdf = FPDF()
    pdf.add_page()

    pdf.add_font("DejaVu", "", FONT_FILE, uni=True)
    pdf.set_font("DejaVu", "", 14)

    pdf.cell(0, 10, t("receipt_for_guest"), ln=True)

    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 8, f"{t('guest_name')}: {guest.name}", ln=True)
    pdf.cell(0, 8, f"{t('room')}: {guest.room_number} ({guest.room_category})", ln=True)
    pdf.cell(0, 8, f"{t('price_per_night')}: {guest.price_per_night:.2f} €", ln=True)
    pdf.cell(0, 8, f"{t('checkin')}: {guest.checkin_date}", ln=True)
    pdf.cell(0, 8, f"{t('checkout')}: {guest.checkout_date or '-'}", ln=True)

    pdf.ln(5)
    pdf.set_font("DejaVu", "", 13)
    pdf.cell(0, 10, t("guest_details_nights"), ln=True)

    pdf.set_font("DejaVu", "", 12)
    pdf.cell(40, 8, t("night"))
    pdf.cell(40, 8, t("paid"), ln=True)

    for n in guest.nights:
        pdf.cell(40, 8, str(n.number))
        pdf.cell(40, 8, t("yes") if n.paid else t("no"), ln=True)

    paid_count = len([n for n in guest.nights if n.paid])
    unpaid_count = len([n for n in guest.nights if not n.paid])
    sum_paid = paid_count * guest.price_per_night
    sum_unpaid = unpaid_count * guest.price_per_night

    pdf.ln(5)
    pdf.set_font("DejaVu", "", 13)
    pdf.cell(0, 10, t("summary"), ln=True)

    pdf.set_font("DejaVu", "", 12)
    pdf.cell(0, 8, f"{t('paid_nights')}: {paid_count} (Summe: {sum_paid:.2f} €)", ln=True)
    pdf.cell(0, 8, f"{t('unpaid_nights')}: {unpaid_count} (Summe: {sum_unpaid:.2f} €)", ln=True)

    pdf.ln(10)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 8, "PDF generated automatically.", ln=True)

    return pdf.output(dest="S").encode("latin1")
