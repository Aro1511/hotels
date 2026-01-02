from typing import List
from models import (
    Guest,
    Room,
    guest_from_dict,
    guest_to_dict,
    room_from_dict,
    room_to_dict,
)
from firebase_db import load_json, save_json


# ---------------------------------------------------------
# Gäste laden & speichern
# ---------------------------------------------------------
def load_guests(hotel_id: str) -> List[Guest]:
    data = load_json(f"{hotel_id}/gaeste")
    return [guest_from_dict(item) for item in data]


def save_guests(hotel_id: str, guests: List[Guest]) -> None:
    data = [guest_to_dict(g) for g in guests]
    save_json(f"{hotel_id}/gaeste", data)


# ---------------------------------------------------------
# Zimmer laden & speichern
# ---------------------------------------------------------
def load_rooms(hotel_id: str) -> List[Room]:
    data = load_json(f"{hotel_id}/raeume")
    return [room_from_dict(item) for item in data]


def save_rooms(hotel_id: str, rooms: List[Room]) -> None:
    data = [room_to_dict(r) for r in rooms]
    save_json(f"{hotel_id}/raeume", data)
