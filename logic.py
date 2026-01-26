from typing import List, Optional, Tuple
from datetime import datetime

from models import Guest, Room, Night
from database import load_guests, save_guests, load_rooms, save_rooms


# ---------------------------------------------------------
# Hilfsfunktionen für IDs
# ---------------------------------------------------------
def _get_next_guest_id(guests: List[Guest]) -> int:
    if not guests:
        return 1
    return max(g.id for g in guests) + 1


# ---------------------------------------------------------
# Zimmer-Funktionen
# ---------------------------------------------------------
def add_room(hotel_id: str, number: int, category: str) -> None:
    rooms = load_rooms(hotel_id)

    for r in rooms:
        if r.number == number:
            raise ValueError(f"Zimmer {number} existiert bereits.")

    new_room = Room(number=number, category=category, occupied=False)
    rooms.append(new_room)
    save_rooms(hotel_id, rooms)


def set_room_occupied(hotel_id: str, room_number: int, occupied: bool) -> None:
    rooms = load_rooms(hotel_id)
    for r in rooms:
        if r.number == room_number:
            r.occupied = occupied
            break
    save_rooms(hotel_id, rooms)


def get_room(hotel_id: str, room_number: int) -> Optional[Room]:
    rooms = load_rooms(hotel_id)
    for r in rooms:
        if r.number == room_number:
            return r
    return None


# ---------------------------------------------------------
# Gäste-Funktionen
# ---------------------------------------------------------
def add_guest(
    hotel_id: str,
    name: str,
    room_number: int,
    room_category: str,
    price_per_night: float,
) -> Guest:
    guests = load_guests(hotel_id)
    rooms = load_rooms(hotel_id)

    room = get_room(hotel_id, room_number)

    # Zimmer existiert nicht → automatisch anlegen
    if room is None:
        room = Room(number=room_number, category=room_category, occupied=False)
        rooms.append(room)

    if room.occupied:
        raise ValueError(f"Zimmer {room_number} ist bereits belegt.")

    new_id = _get_next_guest_id(guests)
    today = datetime.now().strftime("%Y-%m-%d")

    guest = Guest(
        id=new_id,
        name=name,
        room_number=room_number,
        room_category=room_category,
        price_per_night=price_per_night,
        nights=[],
        checkin_date=today,
        checkout_date=None,
        status="checked_in",
    )

    guests.append(guest)
    save_guests(hotel_id, guests)

    # Zimmer belegen
    room.occupied = True
    save_rooms(hotel_id, rooms)

    return guest


def get_guest_by_id(hotel_id: str, guest_id: int) -> Optional[Guest]:
    guests = load_guests(hotel_id)
    for g in guests:
        if g.id == guest_id:
            return g
    return None


def update_guest(hotel_id: str, updated_guest: Guest) -> None:
    guests = load_guests(hotel_id)
    for i, g in enumerate(guests):
        if g.id == updated_guest.id:
            guests[i] = updated_guest
            break
    save_guests(hotel_id, guests)


# ---------------------------------------------------------
# Gast bearbeiten (Name, Zimmer, Kategorie, Preis)
# ---------------------------------------------------------
def update_guest_details(
    hotel_id: str,
    guest_id: int,
    new_name: str,
    new_room_number: int,
    new_room_category: str,
    new_price: float
) -> Guest:

    guests = load_guests(hotel_id)
    rooms = load_rooms(hotel_id)

    guest = get_guest_by_id(hotel_id, guest_id)
    if not guest:
        raise ValueError("Gast nicht gefunden")

    old_room_number = guest.room_number

    # Name aktualisieren
    guest.name = new_name

    # Wenn Zimmer gewechselt wird
    if new_room_number != old_room_number:

        # Altes Zimmer freigeben
        for r in rooms:
            if r.number == old_room_number:
                r.occupied = False
                break

        # Neues Zimmer prüfen
        new_room = get_room(hotel_id, new_room_number)

        # Neues Zimmer existiert nicht → automatisch anlegen
        if new_room is None:
            new_room = Room(number=new_room_number, category=new_room_category, occupied=False)
            rooms.append(new_room)

        # Neues Zimmer darf nicht belegt sein
        if new_room.occupied:
            raise ValueError(f"Zimmer {new_room_number} ist bereits belegt.")

        # Neues Zimmer belegen
        new_room.occupied = True

        # Gast aktualisieren
        guest.room_number = new_room_number

    # Kategorie aktualisieren
    guest.room_category = new_room_category

    # Neuer Preis gilt nur für zukünftige Nächte
    guest.price_per_night = new_price

    # Speichern
    update_guest(hotel_id, guest)
    save_rooms(hotel_id, rooms)

    return guest


# ---------------------------------------------------------
# Nächte
# ---------------------------------------------------------
def add_night_to_guest(hotel_id: str, guest_id: int, paid: bool) -> Guest:
    guests = load_guests(hotel_id)
    for g in guests:
        if g.id == guest_id:
            next_number = 1
            if g.nights:
                next_number = max(n.number for n in g.nights) + 1

            # Jede Nacht speichert ihren eigenen Preis
            g.nights.append(Night(
                number=next_number,
                paid=paid,
                price=g.price_per_night
            ))

            update_guest(hotel_id, g)
            return g

    raise ValueError("Gast nicht gefunden")


def set_night_paid_status(
    hotel_id: str, guest_id: int, night_number: int, paid: bool
) -> Guest:
    guest = get_guest_by_id(hotel_id, guest_id)
    if not guest:
        raise ValueError("Gast nicht gefunden")

    for n in guest.nights:
        if n.number == night_number:
            n.paid = paid
            break

    update_guest(hotel_id, guest)
    return guest


# ---------------------------------------------------------
# Summenberechnung (mit Rückwärtskompatibilität)
# ---------------------------------------------------------
def calculate_nights_summary(guest: Guest) -> Tuple[int, int, float, float]:
    paid_nights = [n for n in guest.nights if n.paid]
    unpaid_nights = [n for n in guest.nights if not n.paid]

    count_paid = len(paid_nights)
    count_unpaid = len(unpaid_nights)

    # Falls alte Nächte kein price-Feld haben → fallback auf guest.price_per_night
    def get_price(n):
        return getattr(n, "price", guest.price_per_night)

    sum_paid = sum(get_price(n) for n in paid_nights)
    sum_unpaid = sum(get_price(n) for n in unpaid_nights)

    return count_paid, count_unpaid, sum_paid, sum_unpaid


# ---------------------------------------------------------
# Suche & Listen
# ---------------------------------------------------------
def search_guests_by_name(hotel_id: str, query: str) -> List[Guest]:
    guests = load_guests(hotel_id)
    query_lower = query.lower()
    return [g for g in guests if query_lower in g.name.lower()]


def list_all_guests(hotel_id: str, include_checked_out: bool = False) -> List[Guest]:
    guests = load_guests(hotel_id)
    if include_checked_out:
        return guests
    return [g for g in guests if g.status == "checked_in"]


# ---------------------------------------------------------
# Checkout & Löschen
# ---------------------------------------------------------
def checkout_guest(hotel_id: str, guest_id: int) -> None:
    guests = load_guests(hotel_id)
    rooms = load_rooms(hotel_id)
    today = datetime.now().strftime("%Y-%m-%d")

    for g in guests:
        if g.id == guest_id:
            g.status = "checked_out"
            g.checkout_date = today

            # Zimmer freigeben
            for r in rooms:
                if r.number == g.room_number:
                    r.occupied = False
                    break
            break

    save_guests(hotel_id, guests)
    save_rooms(hotel_id, rooms)


def delete_guest(hotel_id: str, guest_id: int) -> None:
    guests = load_guests(hotel_id)
    rooms = load_rooms(hotel_id)

    guest_to_delete = None

    for g in guests:
        if g.id == guest_id:
            guest_to_delete = g
            break

    if guest_to_delete is None:
        raise ValueError("Gast nicht gefunden")

    # Zimmer freigeben
    for r in rooms:
        if r.number == guest_to_delete.room_number:
            r.occupied = False
            break

    guests = [g for g in guests if g.id != guest_id]

    save_guests(hotel_id, guests)
    save_rooms(hotel_id, rooms)
