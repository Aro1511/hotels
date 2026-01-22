from firebase_db import db
from auth import hash_password, verify_password
from datetime import datetime

SUPERADMIN_EMAIL = "admin@system.local"
SUPERADMIN_PASSWORD = "admin123"


# ---------------------------------------------------------
# Superadmin automatisch erzeugen, falls nicht vorhanden
# ---------------------------------------------------------
def ensure_superadmin_exists():
    users_ref = db.collection("users").where("role", "==", "superadmin").stream()
    if any(users_ref):
        return True

    db.collection("users").add({
        "email": SUPERADMIN_EMAIL,
        "email_lower": SUPERADMIN_EMAIL.lower(),
        "password": hash_password(SUPERADMIN_PASSWORD),
        "role": "superadmin",
        "tenant_id": "superadmin",
        "active": True,
        "created_at": datetime.utcnow()
    })

    return True


# ---------------------------------------------------------
# Benutzer erstellen (nur customer)
# ---------------------------------------------------------
def create_user(email, password, role, tenant_id):
    if role != "customer":
        raise ValueError("Nur 'customer' ist erlaubt.")

    email_clean = email.strip().lower()

    db.collection("users").add({
        "email": email_clean,
        "email_lower": email_clean,
        "password": hash_password(password),
        "role": "customer",
        "tenant_id": tenant_id,
        "active": True,
        "created_at": datetime.utcnow()
    })


# ---------------------------------------------------------
# Login prüfen (Case-insensitive, eindeutig, stabil)
# ---------------------------------------------------------
def validate_login(email, password):
    email_clean = email.strip().lower()

    # Exakt passenden User suchen
    users_ref = db.collection("users").where("email_lower", "==", email_clean).stream()

    for doc in users_ref:
        user = doc.to_dict()
        user["id"] = doc.id

        # Falls ein alter/kaputter Datensatz ohne Passwort existiert → überspringen
        if "password" not in user:
            continue

        if not user.get("active", True):
            continue

        if verify_password(password, user["password"]):
            return user

    return None
