from fpdf import FPDF, HTMLMixin
from datetime import datetime
from models import Guest


class PDF(FPDF, HTMLMixin):
    pass


def generate_receipt_pdf(guest: Guest, t):
    pdf = PDF()
    pdf.add_page()

    html = f"""
    <h2>{t('receipt_for_guest')}</h2>

    <p><b>{t('guest_name')}:</b> {guest.name}</p>
    <p><b>{t('room')}:</b> {guest.room_number} ({guest.room_category})</p>
    <p><b>{t('price_per_night')}:</b> {guest.price_per_night:.2f} €</p>
    <p><b>{t('checkin')}:</b> {guest.checkin_date}</p>
    <p><b>{t('checkout')}:</b> {guest.checkout_date or '-'}</p>

    <h3>{t('guest_details_nights')}</h3>
    <table border="1" width="100%" align="center">
        <thead>
            <tr>
                <th>{t('night')}</th>
                <th>{t('paid')}</th>
            </tr>
        </thead>
        <tbody>
    """

    for n in guest.nights:
        html += f"""
        <tr>
            <td>{n.number}</td>
            <td>{t('yes') if n.paid else t('no')}</td>
        </tr>
        """

    html += "</tbody></table>"

    paid_count = len([n for n in guest.nights if n.paid])
    unpaid_count = len([n for n in guest.nights if not n.paid])
    sum_paid = paid_count * guest.price_per_night
    sum_unpaid = unpaid_count * guest.price_per_night

    html += f"""
    <h3>{t('summary')}</h3>
    <p>{t('paid_nights')}: {paid_count} (Summe: {sum_paid:.2f} €)</p>
    <p>{t('unpaid_nights')}: {unpaid_count} (Summe: {sum_unpaid:.2f} €)</p>
    """

    pdf.write_html(html)

    return pdf.output(dest="S").encode("latin1")
