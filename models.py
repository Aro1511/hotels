from dataclasses import dataclass, asdict, field
from typing import List, Optional


# ---------------------------------------------------------
# Datenklasse: Nacht
# ---------------------------------------------------------
@dataclass
class Night:
    number: int
    paid: bool = False


# ---------------------------------------------------------
# Datenklasse: Gast
# ---------------------------------------------------------
@dataclass
class Guest:
    id: int
    name: str
    room_number: int
    room_category: str
    price_per_night: float
    nights: List[Night] = field(default_factory=list)
    checkin_date: str = ""
    checkout_date: Optional[str] = None
    status: str = "checked_in"  # "checked_in" oder "checked_out"


# ---------------------------------------------------------
# Datenklasse: Zimmer
# ---------------------------------------------------------
@dataclass
class Room:
    number: int
    category: str  # "Einzel", "Doppel", "Familie", ...
    occupied: bool = False


# ---------------------------------------------------------
# Konvertierung: Guest → dict (für Firebase)
# ---------------------------------------------------------
def guest_to_dict(guest: Guest) -> dict:
    return {
        "id": guest.id,
        "name": guest.name,
        "room_number": guest.room_number,
        "room_category": guest.room_category,
        "price_per_night": guest.price_per_night,
        "nights": [{"number": n.number, "paid": n.paid} for n in guest.nights],
        "checkin_date": guest.checkin_date,
        "checkout_date": guest.checkout_date,
        "status": guest.status,
    }


# ---------------------------------------------------------
# Konvertierung: dict → Guest (aus Firebase)
# ---------------------------------------------------------
def guest_from_dict(data: dict) -> Guest:
    # defensive defaults, falls Firebase-Daten unvollständig sind
    nights_raw = data.get("nights", [])
    nights = [
        Night(
            number=n.get("number", 0),
            paid=n.get("paid", False)
        )
        for n in nights_raw
    ]

    return Guest(
        id=data.get("id", 0),
        name=data.get("name", ""),
        room_number=data.get("room_number", 0),
        room_category=data.get("room_category", ""),
        price_per_night=data.get("price_per_night", 0.0),
        nights=nights,
        checkin_date=data.get("checkin_date", ""),
        checkout_date=data.get("checkout_date"),
        status=data.get("status", "checked_in"),
    )


# ---------------------------------------------------------
# Konvertierung: Room → dict
# ---------------------------------------------------------
def room_to_dict(room: Room) -> dict:
    return asdict(room)


# ---------------------------------------------------------
# Konvertierung: dict → Room
# ---------------------------------------------------------
def room_from_dict(data: dict) -> Room:
    return Room(
        number=data.get("number", 0),
        category=data.get("category", ""),
        occupied=data.get("occupied", False),
    )
