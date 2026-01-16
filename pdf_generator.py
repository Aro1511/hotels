from fpdf import FPDF
from datetime import datetime
from models import Guest


def generate_receipt_pdf(guest: Guest, t):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, t("receipt_for_guest"), ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"{t('guest_name')}: {guest.name}", ln=True)
    pdf.cell(0, 8, f"{t('room')}: {guest.room_number} ({guest.room_category})", ln=True)
    pdf.cell(0, 8, f"{t('price_per_night')}: {guest.price_per_night:.2f} €", ln=True)
    pdf.cell(0, 8, f"{t('checkin')}: {guest.checkin_date}", ln=True)
    pdf.cell(0, 8, f"{t('checkout')}: {guest.checkout_date or '-'}", ln=True)

    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, t("guest_details_nights"), ln=True)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 8, t("night"))
    pdf.cell(40, 8, t("paid"), ln=True)

    pdf.set_font("Arial", "", 12)
    for n in guest.nights:
        pdf.cell(40, 8, str(n.number))
        pdf.cell(40, 8, t("yes") if n.paid else t("no"), ln=True)

    paid_count = len([n for n in guest.nights if n.paid])
    unpaid_count = len([n for n in guest.nights if not n.paid])
    sum_paid = paid_count * guest.price_per_night
    sum_unpaid = unpaid_count * guest.price_per_night

    pdf.ln(5)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, t("summary"), ln=True)

    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"{t('paid_nights')}: {paid_count} (Summe: {sum_paid:.2f} €)", ln=True)
    pdf.cell(0, 8, f"{t('unpaid_nights')}: {unpaid_count} (Summe: {sum_unpaid:.2f} €)", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", "I", 10)
    pdf.cell(0, 8, "PDF generated automatically.", ln=True)

    return pdf.output(dest="S").encode("latin1")
