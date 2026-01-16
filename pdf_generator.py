import fitz  # PyMuPDF
from datetime import datetime
from models import Guest


def generate_receipt_pdf(guest: Guest, t):
    doc = fitz.open()
    page = doc.new_page()

    y = 40
    line_height = 18

    def write(text, size=12):
        nonlocal y
        page.insert_text((40, y), text, fontsize=size)
        y += line_height

    write(t("receipt_for_guest"), 16)
    write("")
    write(f"{t('guest_name')}: {guest.name}")
    write(f"{t('room')}: {guest.room_number} ({guest.room_category})")
    write(f"{t('price_per_night')}: {guest.price_per_night:.2f} €")
    write(f"{t('checkin')}: {guest.checkin_date}")
    write(f"{t('checkout')}: {guest.checkout_date or '-'}")

    write("")
    write(t("guest_details_nights"), 14)

    for n in guest.nights:
        write(f"{t('night')} {n.number}: {t('yes') if n.paid else t('no')}")

    paid_count = len([n for n in guest.nights if n.paid])
    unpaid_count = len([n for n in guest.nights if not n.paid])
    sum_paid = paid_count * guest.price_per_night
    sum_unpaid = unpaid_count * guest.price_per_night

    write("")
    write(t("summary"), 14)
    write(f"{t('paid_nights')}: {paid_count} (Summe: {sum_paid:.2f} €)")
    write(f"{t('unpaid_nights')}: {unpaid_count} (Summe: {sum_unpaid:.2f} €)")

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes
