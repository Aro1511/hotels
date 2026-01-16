from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors
from datetime import datetime
from models import Guest


def generate_receipt_pdf(guest: Guest, t, hotel_name="Hotel"):
    """
    Erzeugt eine PDF-Rechnung für einen Gast.
    Alle Texte sind über t() übersetzbar.
    """

    from io import BytesIO
    buffer = BytesIO()

    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ---------------------------------------------------------
    # Header
    # ---------------------------------------------------------
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, height - 20 * mm, hotel_name)

    c.setFont("Helvetica", 10)
    c.drawString(
        20 * mm,
        height - 30 * mm,
        f"{t('receipt_for_guest')} – {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )

    # ---------------------------------------------------------
    # Gastinformationen
    # ---------------------------------------------------------
    y = height - 50 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, t("guest_details_nights"))
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, y, f"{t('guest_name')}: {guest.name}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"{t('room')}: {guest.room_number} ({guest.room_category})")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"{t('price_per_night')}: {guest.price_per_night:.2f} €")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"{t('checkin')}: {guest.checkin_date}")
    y -= 6 * mm
    c.drawString(20 * mm, y, f"{t('checkout')}: {guest.checkout_date or '-'}")
    y -= 10 * mm

    # ---------------------------------------------------------
    # Tabelle der Nächte
    # ---------------------------------------------------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, t("guest_details_nights"))
    y -= 8 * mm

    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, t("night"))
    c.drawString(60 * mm, y, t("paid"))
    y -= 6 * mm

    c.setFont("Helvetica", 10)
    for n in guest.nights:
        c.drawString(20 * mm, y, str(n.number))
        c.drawString(60 * mm, y, t("yes") if n.paid else t("no"))
        y -= 6 * mm

    # ---------------------------------------------------------
    # Summen
    # ---------------------------------------------------------
    paid_count = len([n for n in guest.nights if n.paid])
    unpaid_count = len([n for n in guest.nights if not n.paid])
    sum_paid = paid_count * guest.price_per_night
    sum_unpaid = unpaid_count * guest.price_per_night

    y -= 10 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, y, t("summary"))
    y -= 8 * mm

    c.setFont("Helvetica", 10)
    c.drawString(
        20 * mm,
        y,
        f"{t('paid_nights')}: {paid_count} (Summe: {sum_paid:.2f} €)"
    )
    y -= 6 * mm
    c.drawString(
        20 * mm,
        y,
        f"{t('unpaid_nights')}: {unpaid_count} (Summe: {sum_unpaid:.2f} €)"
    )
    y -= 10 * mm

    # ---------------------------------------------------------
    # Footer
    # ---------------------------------------------------------
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(colors.grey)
    c.drawString(20 * mm, 10 * mm, t("guest_checked_out"))

    c.save()

    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
