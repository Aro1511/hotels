from firebase_db import db
from auth import hash_password, verify_password
from datetime import datetime

SUPERADMIN_EMAIL = "admin@system.local"
SUPERADMIN_PASSWORD = "admin123"


# ---------------------------------------------------------
# Automatische Reparatur aller User
# ---------------------------------------------------------
def repair_users():
    users_ref = db.collection("users").stream()

    for doc in users_ref:
        data = doc.to_dict()
        updates = {}

        # Email normalisieren
        if "email" in data:
            email_clean = data["email"].strip().lower()
            if data["email"] != email_clean:
                updates["email"] = email_clean

            # email_lower ergänzen
            if data.get("email_lower") != email_clean:
                updates["email_lower"] = email_clean

        # Falls Reparaturen nötig → speichern
        if updates:
            db.collection("users").document(doc.id).update(updates)


# ---------------------------------------------------------
# Superadmin automatisch erzeugen, falls nicht vorhanden
# ---------------------------------------------------------
def ensure_superadmin_exists():
    repair_users()  # <<< WICHTIG: Reparatur beim Start

    users_ref = db.collection("users").where("role", "==", "superadmin").stream()
    if any(users_ref):
        return True

    email_clean = SUPERADMIN_EMAIL.lower()

    db.collection("users").add({
        "email": email_clean,
        "email_lower": email_clean,
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
    repair_users()  # <<< WICHTIG: Reparatur vor jedem Login

    email_clean = email.strip().lower()

    users_ref = db.collection("users").where("email_lower", "==", email_clean).stream()

    for doc in users_ref:
        user = doc.to_dict()
        user["id"] = doc.id

        if "password" not in user:
            continue

        if not user.get("active", True):
            continue

        if verify_password(password, user["password"]):
            return user

    return None


# ---------------------------------------------------------
# Passwort ändern (für eingeloggte Mandanten)
# ---------------------------------------------------------
def change_password(user_id, old_password, new_password):
    user_ref = db.collection("users").document(user_id)
    snap = user_ref.get()
    if not snap.exists:
        return False, "User existiert nicht."

    user = snap.to_dict()

    if "password" not in user:
        return False, "Kein Passwort gesetzt."

    if not verify_password(old_password, user["password"]):
        return False, "Das alte Passwort ist falsch."

    new_hash = hash_password(new_password)
    user_ref.update({"password": new_hash})

    return True, "Passwort erfolgreich geändert."
