import fitz  # PyMuPDF
import csv
import io
from models import Guest


# ---------------------------------------------------------
# PDF-Rechnung
# ---------------------------------------------------------
def generate_receipt_pdf(guest: Guest, t):
    doc = fitz.open()
    page = doc.new_page()

    y = 40
    line_height = 18

    def write(text, size=12):
        nonlocal y
        page.insert_text((40, y), text, fontsize=size)
        y += line_height

    # Kopfbereich
    write(t("receipt_for_guest"), 16)
    write("")
    write(f"{t('guest_name')}: {guest.name}")
    write(f"{t('room')}: {guest.room_number} ({guest.room_category})")
    write(f"{t('price_per_night')}: {guest.price_per_night:.2f} €")
    write(f"{t('checkin')}: {guest.checkin_date}")
    write(f"{t('checkout')}: {guest.checkout_date or '-'}")

    # Nächte
    write("")
    write(t("guest_details_nights"), 14)

    paid_count = 0
    unpaid_count = 0

    for n in guest.nights:
        write(f"{t('night')} {n.number}: {t('yes') if n.paid else t('no')}")
        if n.paid:
            paid_count += 1
        else:
            unpaid_count += 1

    sum_paid = paid_count * guest.price_per_night
    sum_unpaid = unpaid_count * guest.price_per_night

    # Zusammenfassung
    write("")
    write(t("summary"), 14)
    write(f"{t('paid_nights')}: {paid_count} (Summe: {sum_paid:.2f} €)")
    write(f"{t('unpaid_nights')}: {unpaid_count} (Summe: {sum_unpaid:.2f} €)")
    write(f"Gesamt: {(sum_paid + sum_unpaid):.2f} €")

    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


# ---------------------------------------------------------
# CSV-Rechnung
# ---------------------------------------------------------
def generate_receipt_csv(guest: Guest, t):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    # Kopfbereich
    writer.writerow([t("receipt_for_guest")])
    writer.writerow([])
    writer.writerow([t("guest_name"), guest.name])
    writer.writerow([t("room"), f"{guest.room_number} ({guest.room_category})"])
    writer.writerow([t("price_per_night"), f"{guest.price_per_night:.2f} €"])
    writer.writerow([t("checkin"), guest.checkin_date])
    writer.writerow([t("checkout"), guest.checkout_date or "-"])
    writer.writerow([])

    # Nächte
    writer.writerow([t("guest_details_nights")])
    writer.writerow([t("night"), t("paid")])

    paid_count = 0
    unpaid_count = 0

    for n in guest.nights:
        writer.writerow([n.number, t("yes") if n.paid else t("no")])
        if n.paid:
            paid_count += 1
        else:
            unpaid_count += 1

    sum_paid = paid_count * guest.price_per_night
    sum_unpaid = unpaid_count * guest.price_per_night

    # Zusammenfassung
    writer.writerow([])
    writer.writerow([t("summary")])
    writer.writerow([t("paid_nights"), paid_count, f"{sum_paid:.2f} €"])
    writer.writerow([t("unpaid_nights"), unpaid_count, f"{sum_unpaid:.2f} €"])
    writer.writerow(["Gesamt", "", f"{(sum_paid + sum_unpaid):.2f} €"])

    return output.getvalue().encode("utf-8")
